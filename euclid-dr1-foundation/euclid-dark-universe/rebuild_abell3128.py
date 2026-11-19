"""Rebuild the Abell 3128 sightline figures from calibrated MER cutouts."""
from pathlib import Path
import argparse
import csv
import hashlib
from itertools import product
import json

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import mad_std, sigma_clip
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d

from arc_geometry import CENTRE, PA, RADII, sample, strongest_ridge

BANDS = ("NIR-H", "VIS", "DES-G")
RGB_GAIN = np.array([0.55, 2.0, 5.0])
RGB_SIGMA = (1.15, 0.75, 1.10)
CROP = slice(100, 391)
CONTROL = (np.arange(-65, 125, 5), np.arange(-40, 100, 5), np.arange(-100, 60, 5))
SMOOTHING = (0.05, 0.10, 0.20)
CONTOUR_LEVELS = (8, 16, 32, 64)
LABEL = {"VIS": "Euclid VIS", "DES-G": "Blanco DECam g"}


def background(data, sky):
    clipped = sigma_clip(data[sky], sigma=3, maxiters=5, stdfunc="mad_std").compressed()
    return float(np.median(clipped)), float(mad_std(clipped))


def load_bands(source):
    manifest = json.loads((source / "arc_image_manifest.json").read_text())
    origins = {row["band"]: row for row in manifest}
    expected = json.loads((source / "fits_sha256.json").read_text())
    records = {}
    x_test = [0, 490, 0, 490, 245]
    y_test = [0, 0, 490, 490, 245]
    ref = None
    for band in BANDS:
        path = source / f"arc_{band}.fits"
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != expected[path.name]:
            raise ValueError(f"Unexpected FITS hash for {path.name}")
        data, h = fits.getdata(path, header=True)
        wcs = WCS(h).celestial
        points = wcs.pixel_to_world(x_test, y_test)
        if ref is None:
            ref = points
        delta = float(points.separation(ref).arcsec.max())
        if data.shape != (491, 491) or not np.isfinite(data).all() or delta > .001:
            raise ValueError(f"Image or WCS grid check failed for {band}")
        records[band] = (data.astype(float), h, wcs, {
            "input_file": path.name, "sha256": sha, "archive_product": origins[band]["url"],
            "archive_etag": origins[band]["etag"], "native_unit": h["BUNIT"],
            "AB_zero_point": h["MAGZERO"], "WCS_max_grid_separation_arcsec": delta,
        })
    return records


def prepare_displays(records, center):
    w = records["VIS"][2]
    xc, yc = w.world_to_pixel(center)
    scale = (w.proj_plane_pixel_scales()[0]).to_value(u.arcsec)
    if not np.allclose(w.pixel_scale_matrix * 3600, [[-scale, 0], [0, scale]], atol=1e-7):
        raise ValueError("Expected north-up, east-left tangent-plane grid")
    yy, xx = np.indices(records["VIS"][0].shape)
    sky = ((np.hypot(xx-xc, yy-yc) * scale > 16.8)
           & (xx > 10) & (xx < 480) & (yy > 10) & (yy < 480))
    display_channels = []
    display_noise = []
    for band, gain, smooth in zip(BANDS, RGB_GAIN, RGB_SIGMA, strict=True):
        data, h, _, meta = records[band]
        filtered = gaussian_filter(data, smooth)
        zero, noise = background(filtered, sky)
        conversion = 10**(0.4 * (30 - h["MAGZERO"]))
        display_channels.append(np.maximum(filtered - zero - 1.5*noise, 0) * conversion * gain)
        display_noise.append(noise * conversion * gain)
        native_zero, native_noise = background(data, sky)
        meta.update(rgb_gain=float(gain), rgb_smoothing_sigma_arcsec=smooth*scale,
                    rgb_sky_native=zero, rgb_sky_mad_sigma_native=noise,
                    unsmoothed_sky_native=native_zero, unsmoothed_sky_mad_sigma_native=native_noise)
    stack = np.stack(display_channels, axis=-1)
    intensity = stack.mean(axis=-1)
    white = float(5 * np.percentile(intensity[CROP, CROP], 98.8))
    soft = max(2 * np.linalg.norm(display_noise)/3, white/28)
    tone = np.arcsinh(intensity/soft) / np.arcsinh(white/soft)
    factor = np.divide(tone, intensity, out=np.zeros_like(intensity), where=intensity > 0)
    rgb = stack * factor[..., None]
    rgb /= np.maximum(1, rgb.max(axis=-1))[..., None]

    vis = records["VIS"][0]
    zero, noise = background(vis, sky)
    linear = np.maximum(vis-zero-0.75*noise, 0)
    vis_white = float(3 * np.percentile(linear[CROP, CROP], 99.8))
    vis_view = np.clip(np.arcsinh(linear/(2*noise))/np.arcsinh(vis_white/(2*noise)), 0, 1)
    contour_image = gaussian_filter(vis, 2.0)
    contour_zero, contour_noise = background(contour_image, sky)
    contour = (contour_image - contour_zero) / contour_noise
    extent = ((CROP.start-.5-xc)*scale, (CROP.stop-.5-xc)*scale,
              (CROP.start-.5-yc)*scale, (CROP.stop-.5-yc)*scale)
    metadata = {
        "pixel_scale_arcsec": float(scale), "field_width_arcsec": float((CROP.stop-CROP.start)*scale),
        "sky_selection": "radius >16.8 arcsec, excluding 11 outer pixels on each side",
        "sky_estimator": "median and 1.4826 × MAD after iterative 3σ clipping",
        "RGB_sky_floor_sigma": 1.5, "RGB_asinh_softening": float(soft), "RGB_asinh_white": white,
        "VIS_asinh_white_native": vis_white,
        "VIS_contour_smoothing_sigma_arcsec": 2.0*scale,
        "VIS_contour_sky_native": contour_zero, "VIS_contour_sky_mad_sigma_native": contour_noise,
        "VIS_contour_levels_in_smoothed_sky_mad_sigma": CONTOUR_LEVELS,
        "channels": {band: records[band][3] for band in BANDS},
    }
    return rgb[CROP, CROP], vis_view[CROP, CROP], contour[CROP, CROP], extent, metadata


def arc_sensitivity(records, center):
    offsets = [(0., 0.)] + list(product((0.10, 0.25), range(0, 360, 45)))
    sectors = PA[:, None] + np.linspace(-2.5, 2.5, 11)
    summary = {}
    for band in ("VIS", "DES-G"):
        data, _, wcs, _ = records[band]
        grids = []
        nominal = None
        for distance, bearing in offsets:
            shifted = center.directional_offset_by(bearing*u.deg, distance*u.arcsec)
            polar = sample(data, wcs, shifted, sectors.ravel(), RADII)
            profile = np.median(polar.reshape(len(PA), 11, len(RADII)), axis=1)
            for index, angles in enumerate(CONTROL):
                control = np.median(sample(data, wcs, shifted, angles, RADII), axis=0)
                for smooth in SMOOTHING:
                    values = gaussian_filter1d(profile-control, smooth/(RADII[1]-RADII[0]), axis=1)
                    ridges = np.array([strongest_ridge(row) for row in values], dtype=float)
                    grids.append(ridges)
                    if distance == 0 and index == 0 and smooth == .10:
                        nominal = ridges
        table = np.array(grids)
        summary[band] = {
            "nominal": nominal, "min": np.nanmin(table, axis=0), "max": np.nanmax(table, axis=0),
            "usable": np.isfinite(table).sum(axis=0), "tried": len(table),
        }
    return summary


def image_figure(rgb, vis, contour, extent):
    fig, axes = plt.subplots(1, 3, figsize=(12, 5.10))
    fig.subplots_adjust(left=.052, right=.974, top=.759, bottom=.190, wspace=.108)
    fig.text(.052,.94,"The gravitational arc in the Abell 3128 sightline",
             size=20, weight="semibold", va="top")
    fig.text(.052,.865,"DES J0330−5228   |   Euclid DR1-Foundation MER tile 102017310",
             size=10.5, color=".28")
    labels = ("Composite RGB", "Euclid VIS", "Euclid VIS brightness contours")
    for ax, image, letter, title in zip(axes, [rgb, vis, vis], "abc", labels, strict=True):
        ax.imshow(image, origin="lower", extent=extent, cmap="gray", vmin=0, vmax=1,
                  interpolation="nearest")
        ax.set(xticks=[], yticks=[])
        ax.set_title(f"({letter}) {title}", loc="left", fontsize=11, pad=8)
    first = axes[0]
    first.annotate("", (-11.3, 12.3), (-11.3, 9.5), arrowprops={"arrowstyle": "->", "color": "white"})
    first.annotate("", (-14.1, 9.5), (-11.3, 9.5), arrowprops={"arrowstyle": "->", "color": "white"})
    first.text(-11.3, 12.45, "N", ha="center", color="white", fontsize=8)
    first.text(-13.1, 8.2, "E", ha="center", color="white", fontsize=8)
    first.plot([-12.6,-7.6],[-12.6,-12.6],color="white",lw=1.45)
    first.text(-10.1,-11.9,"5″",ha="center",color="white",fontsize=9)
    axes[2].contour(contour, levels=CONTOUR_LEVELS, origin="lower", extent=extent,
                    colors=[".62",".73",".84","1"], linewidths=.64, alpha=.88)
    fig.text(.052,.143,"(a) R = NISP H, G = VIS, B = DECam g. Shared asinh stretch after sky subtraction and light display smoothing.",
             size=9)
    fig.text(.052,.104,"(b) VIS at its original sampling.  (c) VIS light contours at 8, 16, 32 and 64 × the background spread after 0.20″ Gaussian smoothing.",
             size=9)
    fig.text(.052,.047,"Biswajit Jana  |  Figure preparation  ·  Imaging ESA/Euclid/Euclid Consortium/NASA and DES/DECam via IRSA",
             size=8.4,color=".30")
    return fig


def arc_figure(summary):
    fig, ax = plt.subplots(figsize=(12, 5.10))
    fig.subplots_adjust(left=.100, right=.965, top=.742, bottom=.28)
    fig.text(.052,.94,"Arc-ridge measurements and extraction sensitivity",
             size=20,weight="semibold",va="top")
    fig.text(.052,.863,"DES J0330−5228   |   10 sectors from 175° to 220° east of north",
             size=10.5,color=".28")
    for band, offset, marker, color in [("VIS", -.48, "o", ".12"), ("DES-G", .48, "s", ".45")]:
        s = summary[band]
        nominal = s["nominal"]
        ax.errorbar(PA+offset, nominal, yerr=[nominal-s["min"],s["max"]-nominal], fmt=marker,
                    color=color, capsize=3, lw=1.05, markersize=5, label=LABEL[band])
    ax.set(xlabel="Sector-centre position angle (deg E of N)", ylabel="Ridge radius (arcsec)", xticks=PA)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y",color=".89")
    ax.set_axisbelow(True)
    ax.legend(frameon=False,loc="upper right",ncols=2)
    fig.text(.052,.137,"Markers show the baseline extraction. Whiskers span 153 settings per band over centre, background sector and radial smoothing choices.",
             size=9.1)
    fig.text(.052,.096,"VIS whiskers at 175° and 180° reach the 7.9″ search boundary. Series are offset in angle for legibility. All settings reuse the same pixels.",
             size=9.1)
    fig.text(.052,.045,"Biswajit Jana  |  Figure preparation  ·  Euclid DR1-Foundation and DES/DECam imaging",
             size=8.4,color=".30")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path("inputs"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = load_bands(args.inputs)
    center = SkyCoord(*CENTRE, unit="deg")
    rgb, vis, contour, extent, metadata = prepare_displays(records, center)
    summary = arc_sensitivity(records, center)
    with (args.output/"arc_ridge_sensitivity.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["band", "pa_deg", "nominal_arcsec", "min_arcsec", "max_arcsec", "usable", "tried"])
        for band, s in summary.items():
            for pa, value, lo, hi, used in zip(PA,s["nominal"],s["min"],s["max"],s["usable"],strict=True):
                writer.writerow([band,pa,*[round(float(v),4) for v in (value,lo,hi)],used,s["tried"]])
    (args.output/"image_processing.json").write_text(json.dumps(metadata, indent=2)+"\n")
    image = image_figure(rgb, vis, contour, extent)
    arc = arc_figure(summary)
    image.savefig(args.output/"Abell3128_FITS_Rebuild.png",dpi=250)
    plt.imsave(args.output/"Abell3128_RGB.png", rgb, origin="lower")
    with PdfPages(args.output/"Abell3128_FITS_Figures.pdf", metadata={
        "Title": "Abell 3128 sightline: FITS rebuild and arc extraction sensitivity", "Author": "Biswajit Jana"
    }) as pdf:
        pdf.savefig(image)
        pdf.savefig(arc)
    plt.close("all")


if __name__ == "__main__":
    main()
