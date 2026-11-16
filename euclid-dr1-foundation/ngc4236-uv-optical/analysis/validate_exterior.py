"""Check exterior UV knots against Gaia DR3 and the SINGS narrow-band footprint."""
import argparse
import csv
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np

from measure import from_plane, mad, optical_score


def load_catalogue(path):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    columns = ("ra", "dec", "parallax", "parallax_error", "pmra", "pmra_error",
               "pmdec", "pmdec_error", "phot_g_mean_mag", "ruwe")
    values = {key: np.array([float(row[key]) if row[key] else np.nan for row in rows])
              for key in columns}
    return rows, values


def gaia_positions(values, date):
    # Shift the position along the local tangent plane. Sources without a measured
    # motion retain their J2016.0 coordinates and cannot pass the foreground cut.
    years = Time(date).jyear - 2016
    catalog = SkyCoord(values["ra"], values["dec"], unit="deg")
    return catalog.spherical_offsets_by(
        np.nan_to_num(values["pmra"]) * years * u.mas,
        np.nan_to_num(values["pmdec"]) * years * u.mas,
    )


def narrowband_coverage(image, wcs, pos):
    scale = proj_plane_pixel_scales(wcs)[0] * 3600
    x, y = map(float, wcs.world_to_pixel(pos))
    ix, iy = round(x), round(y)
    half = int(np.ceil(6 / scale)) + 1
    if not (half <= ix < image.shape[1] - half and half <= iy < image.shape[0] - half):
        return 0.0
    stamp = image.section[iy-half:iy+half+1, ix-half:ix+half+1]
    yy, xx = np.indices(stamp.shape)
    aperture = np.hypot(xx + ix - half - x, yy + iy - half - y) * scale <= 6
    return float(np.mean(np.isfinite(stamp[aperture]) & (stamp[aperture] != 0)))


def geometry_counts(knots):
    major = np.array([float(row["major_arcsec"]) for row in knots])
    minor = np.array([float(row["minor_arcsec"]) for row in knots])
    return {str(scale): int(np.count_nonzero(np.hypot(major/657, minor/216) > scale))
            for scale in (0.9, 1, 1.05, 1.1)}


def plot_coverage(ha, wcs, rows, sky, output):
    stride = 5
    image = np.asarray(ha.data[::stride, ::stride])
    view = np.where(image != 0, np.arcsinh(image / 0.004), np.nan)
    # Keep native pixel coordinates on the axes so the FITS CD matrix is used
    # unchanged. Transposing puts RA on the horizontal axis.
    full_wcs = wcs.swapaxes(0, 1)
    extent = (-stride/2, stride*(view.shape[0]-.5),
              -stride/2, stride*(view.shape[1]-.5))
    fig = plt.figure(figsize=(6.2, 5.8), layout="constrained")
    ax = fig.add_subplot(projection=full_wcs)
    ax.set_facecolor("#393d48")
    ax.imshow(view.T, vmin=-1.6, vmax=3.0, cmap="Greys_r", origin="lower", extent=extent)
    theta = np.linspace(0, 2*np.pi, 361)
    x, y = full_wcs.world_to_pixel(from_plane(657*np.cos(theta), 216*np.sin(theta)))
    ax.plot(x, y, "--", color="#55d1cb", alpha=.85, lw=1.25, label=r"Adopted $D_{25}$")
    x, y = full_wcs.world_to_pixel(sky)
    for supported, color, label in [(True, "#ffcb72", "Usable SINGS overlap"),
                                     (False, "#faa4bb", "Incomplete overlap")]:
        mask = np.array([row["sings_supported"] for row in rows]) == supported
        ax.scatter(x[mask], y[mask], s=35, ec=color, fc="none", lw=1.4, label=label)
    ax.set(xlim=(500, 3420), ylim=(5560, 1280), title="NGC 4236 · SINGS narrow-band footprint")
    ax.coords["ra"].set_axislabel("Right ascension (J2000)")
    ax.coords["dec"].set_axislabel("Declination (J2000)")
    ax.coords["ra"].set_ticks(number=4)
    ax.coords["ra"].set_ticklabel(exclude_overlapping=True)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.14), fontsize=8,
              ncol=2, frameon=False)
    fig.savefig(output, dpi=180, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    analysis = Path(__file__).parent
    with (analysis / "outer_knots.csv").open() as stream:
        knots = list(csv.DictReader(stream))
    with (analysis / "knots.csv").open() as stream:
        strip_knots = [row for row in csv.DictReader(stream)
                       if row["vis_score"] and int(row["controls_n"]) >= 3]
    sky = SkyCoord([float(row["ra_deg"]) for row in knots],
                   [float(row["dec_deg"]) for row in knots], unit="deg")
    gaia_rows, gaia = load_catalogue(analysis / "gaia_dr3_field.csv")
    galex_date = fits.getheader(args.data / "fuv.fits")["OBS-DATE"]
    gaia_uv = gaia_positions(gaia, galex_date)
    # Midpoint circa 2025.0 for the possible DR1-F Wide observation interval.
    gaia_vis = gaia_positions(gaia, "2025-01-01")
    uv_index, uv_dist, _ = sky.match_to_catalog_sky(gaia_uv)

    rows = []
    with (fits.open(args.data / "vis.fits") as sc,
          fits.open(args.data / "vis_flag.fits") as fl,
          fits.open(args.data / "sings_ha.fits") as ha,
          fits.open(args.data / "sings_r.fits") as red):
        wvis, wha, wr = [WCS(h[0].header).celestial for h in (sc, ha, red)]
        for index, (knot, pos) in enumerate(zip(knots, sky, strict=True)):
            result = optical_score(sc[0], fl[0], wvis, pos)
            if result is None:
                raise ValueError(f"No VIS measurement for exterior candidate {knot['id']}")
            np.testing.assert_allclose(result[0], float(knot["vis_score"]), rtol=1e-6)
            peak = result[4]
            dist = peak.separation(gaia_vis).arcsec
            matched = int(np.argmin(dist))
            matched_uv_dist = float(pos.separation(gaia_uv[matched]).arcsec)
            astrometric_snr = np.array([
                gaia[key][matched] / gaia[key+"_error"][matched]
                for key in ("parallax", "pmra", "pmdec")
            ])
            foreground = bool(dist[matched] <= .7 and matched_uv_dist <= 3
                              and gaia["ruwe"][matched] < 1.4 and (
                                  astrometric_snr[0] >= 5
                                  or np.any(np.abs(astrometric_snr[1:]) >= 5)))
            ha_coverage = narrowband_coverage(ha[0], wha, pos)
            r_coverage = narrowband_coverage(red[0], wr, pos)
            rows.append({
                "id": int(knot["id"]), "vis_peak_ra_deg": peak.ra.deg,
                "vis_peak_dec_deg": peak.dec.deg, "vis_uv_arcsec": result[1],
                "nearest_gaia_to_uv": gaia_rows[uv_index[index]]["source_id"],
                "nearest_gaia_to_uv_arcsec": float(uv_dist[index].arcsec),
                "nearest_gaia_to_vis": gaia_rows[matched]["source_id"],
                "nearest_gaia_to_vis_arcsec": float(dist[matched]),
                "vis_nearest_gaia_at_uv_epoch_arcsec": matched_uv_dist,
                "gaia_parallax_over_error": astrometric_snr[0] if np.isfinite(astrometric_snr[0]) else None,
                "gaia_pmra_over_error": astrometric_snr[1] if np.isfinite(astrometric_snr[1]) else None,
                "gaia_pmdec_over_error": astrometric_snr[2] if np.isfinite(astrometric_snr[2]) else None,
                "gaia_ruwe": gaia_rows[matched]["ruwe"],
                "foreground_astrometry": foreground,
                "narrowband_coverage": ha_coverage, "r_coverage": r_coverage,
                "sings_supported": min(ha_coverage, r_coverage) >= .9,
            })
        plot_coverage(ha[0], wha, rows, sky, args.output / "sings_coverage.png")
    summary = {
        "gaia_rows": len(gaia_rows),
        "gaia_vis_within_0p7_and_uv_within_3_ids": [
            row["id"] for row in rows if row["nearest_gaia_to_vis_arcsec"] <= .7
            and row["vis_nearest_gaia_at_uv_epoch_arcsec"] <= 3],
        "foreground_astrometry_ids": [row["id"] for row in rows if row["foreground_astrometry"]],
        "gaia_vis_close_by_radius_arcsec": {
            str(radius): [row["id"] for row in rows
                          if row["nearest_gaia_to_vis_arcsec"] <= radius
                          and row["vis_nearest_gaia_at_uv_epoch_arcsec"] <= 3]
            for radius in (.5, .7, 1)
        },
        "sings_overlap_ids": [row["id"] for row in rows if row["sings_supported"]],
        "sings_zero_narrowband_fraction_ids": [
            row["id"] for row in rows if row["narrowband_coverage"] == 0],
        "outside_scaled_ellipse_strips": geometry_counts(strip_knots),
        "outside_scaled_ellipse_outer": geometry_counts(knots),
    }
    with (args.output / "exterior_validation.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = json.dumps(summary, indent=2) + "\n"
    (args.output / "exterior_validation.json").write_text(report)
    print(report, end="")


if __name__ == "__main__":
    main()
