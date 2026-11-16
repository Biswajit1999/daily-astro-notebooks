"""Reproduce the EDF-N pair's catalogue matches, image panels and line diagnostics."""

import argparse
import json
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18
from astropy.io import fits
from astropy.visualization import make_lupton_rgb
from astropy.wcs import WCS
from matplotlib import pyplot as plt
from matplotlib.colors import AsinhNorm
import numpy as np
import pandas as pd
from scipy.ndimage import map_coordinates

from audit_grism_halpha import DAY02, fit_window, get_hats_spectrum
from audit_vis_apertures import VIS_INVALID

PAIR = DAY02 / "targets" / "pair"
COLORS = ("#006b80", "#a54f12")
TILE = 101834632
TRANSITIONS = (("BGS", "[O III] λ5008", 5008.24), ("RGS", "Hα region", 6564.61))
WIDTH = "sigma_30A"


def read_targets(inputs):
    targets = pd.read_csv(inputs / "dr1_targets.csv", dtype={"object_id": str})
    q1 = pd.read_csv(inputs / "q1_nearby.csv", dtype={"object_id": str})
    positions = SkyCoord(targets.ra_deg, targets.dec_deg, unit="deg")
    q1_positions = SkyCoord(q1.right_ascension, q1.declination, unit="deg")
    nearest, offset, _ = positions.match_to_catalog_sky(q1_positions)
    if len(set(nearest)) != len(nearest) or np.any(offset.arcsec > 0.5):
        raise ValueError("Missing or ambiguous Q1 match to a DR1 source")
    targets["q1_object_id"] = q1.object_id.iloc[nearest].to_numpy()
    targets["q1_offset_arcsec"] = offset.arcsec
    targets["lookback_Gyr_if_spe_z"] = Planck18.lookback_time(targets.spe_z).to_value(u.Gyr)
    targets["luminosity_distance_Gpc_if_spe_z"] = Planck18.luminosity_distance(
        targets.spe_z).to_value(u.Gpc)
    targets["kpc_per_arcsec_if_spe_z"] = Planck18.kpc_proper_per_arcmin(
        targets.spe_z).to_value(u.kpc / u.arcmin) / 60
    return targets, positions


def reproject(hdu, sky):
    sx, sy = WCS(hdu.header).world_to_pixel(sky)
    return map_coordinates(hdu.data.astype(float), [sy, sx], order=1,
                           mode="constant", cval=np.nan)


def plot_images(inputs, output, positions):
    with fits.open(inputs / "image_stamps.fits.gz") as hdus:
        vis = hdus["VIS"]
        ygrid, xgrid = np.indices(vis.shape)
        wcs = WCS(vis.header)
        sky = wcs.pixel_to_world(xgrid, ygrid)
        x, y = wcs.world_to_pixel(positions)
        scale = wcs.proj_plane_pixel_scales()[0].to_value(u.arcsec)
        channels = {}
        for band in ("VIS", "NIR-J", "NIR-H"):
            hdu = hdus[band]
            pixels = hdu.data.astype(float) if band == "VIS" else reproject(hdu, sky)
            channels[band] = ((pixels - np.nanmedian(pixels))
                              * 10 ** ((23.9 - hdu.header["MAGZERO"]) / 2.5))
        hsc = reproject(hdus["HSC-I2"], sky)
        flag_hdu = hdus["VIS-FLAG"]
        np.testing.assert_allclose(WCS(flag_hdu.header).world_to_pixel(positions), (x, y),
                                   atol=0.01, rtol=0)
        invalid = (flag_hdu.data & VIS_INVALID) != 0
    local = ((xgrid - x[0])**2 + (ygrid - y[0])**2 < 15**2) | (
        (xgrid - x[1])**2 + (ygrid - y[1])**2 < 15**2)
    red, green, blue = [channels[name] for name in ("NIR-H", "NIR-J", "VIS")]
    stretch = np.percentile(((red + green + blue) / 3)[local], 99.5) * 0.34
    rgb = make_lupton_rgb(red, green, blue, minimum=0, stretch=stretch, Q=4)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.85), layout="constrained")
    axes[0].imshow(rgb, origin="lower", interpolation="nearest")
    for ax, pixels in zip(axes[1:], (blue, hsc), strict=True):
        lo = np.nanpercentile(pixels, 5)
        hi = np.nanpercentile(pixels[local], 99.6)
        ax.imshow(pixels, origin="lower", cmap="gray", interpolation="nearest",
                  norm=AsinhNorm(linear_width=(hi - lo) * 0.085, vmin=lo, vmax=hi))
    for ax, title in zip(axes, ("Euclid RGB", "Euclid VIS", "Subaru HSC i2"), strict=True):
        for label, xi, yi, color in zip("AB", x, y, ("#42d8f1", "#ffac63"), strict=True):
            ax.scatter(xi, yi, s=100, facecolor="none", edgecolor=color, linewidth=1.2)
            ax.annotate(label, (xi, yi), xytext=(10, 2), textcoords="offset points",
                        color=color, weight="bold")
        ax.plot([6, 6 + 1 / scale], [6, 6], color="white", lw=1.5)
        ax.text(6 + 0.5 / scale, 8, "1″", color="white", ha="center", fontsize=8)
        ax.set_title(title)
        ax.set_axis_off()
    fig.suptitle("Two sources in Euclid Deep Field North")
    fig.supxlabel("DR1-Foundation tile 101834632 · RGB = NISP H, NISP J, VIS")
    fig.savefig(output / "Euclid_pair_RGB.png", dpi=160)
    plt.close(fig)
    return [int(np.count_nonzero(invalid[np.hypot(xgrid - xi, ygrid - yi) * scale <= 1.0]))
            for xi, yi in zip(x, y, strict=True)]


def measure_lines(inputs, output, targets):
    spectra = pd.read_parquet(inputs / "sir_1d.parquet")
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.7), layout="constrained")
    rows = []
    for target, panels, color in zip(targets.itertuples(), axes, COLORS, strict=True):
        for ax, (grism, feature, rest) in zip(panels, TRANSITIONS, strict=True):
            spectrum, count = get_hats_spectrum(spectra, int(target.object_id), TILE, grism)
            if count != 1:
                raise ValueError(f"Expected one {grism} spectrum for {target.object_id}")
            centre = rest * (1 + target.spe_z)
            strict, strict_window = fit_window(spectrum, centre)
            relaxed, relaxed_window = fit_window(spectrum, centre, allow_low_snr=True)
            for mask_rule, diagnostic in (("strict", strict), ("allow_mask_2", relaxed)):
                formal = diagnostic.get(f"{WIDTH}_formal_snr")
                rms = diagnostic.get(f"{WIDTH}_sideband_rms")
                rows.append({"object_id": target.object_id, "grism": grism,
                             "feature": feature, "mask_rule": mask_rule,
                             "centre_A": centre, "status": diagnostic["status"],
                             "core_bins": diagnostic["bins_in_core"],
                             "usable_core": diagnostic["usable_core"],
                             "mask_2_core": diagnostic["core_bins_masked_low_snr_only"],
                             "formal_snr": formal,
                             "adjusted_snr": formal / max(1.0, rms) if formal is not None else None})
            show_relaxed = strict["status"] != "fitted" and relaxed["status"] == "fitted"
            frame = relaxed_window if show_relaxed else strict_window
            wave = frame.wavelength / 10_000
            good = frame.usable
            ax.plot(wave, frame.signal.where(frame.ndith > 0), color="0.62", lw=1)
            ax.scatter(wave[good], frame.signal[good], color=color, s=10)
            if "model" in frame:
                ax.plot(wave, frame.model, color=color, lw=1.4)
            if show_relaxed:
                added = good & frame["mask"].eq(2)
                ax.scatter(wave[added], frame.signal[added], color=color, marker="x", s=30)
                annotation = f"Strict fit unavailable\nWarning-inclusive S/N {rows[-1]['adjusted_snr']:.1f}"
            elif strict["status"] == "fitted":
                annotation = f"Strict adjusted S/N {rows[-2]['adjusted_snr']:.1f}"
            else:
                annotation = strict["status"].replace("_", " ")
            ax.text(.03, .95, annotation, transform=ax.transAxes, va="top", fontsize=9,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9})
            ax.axvline(centre / 10_000, ls=":", color="0.25", lw=1)
            ax.set(title=f"{target.label} · {feature} · SPE z = {target.spe_z:.4f}",
                   xlabel="Observed wavelength (µm)")
            if grism == "BGS":
                ax.set_ylabel("Flux density (10⁻¹⁶ erg s⁻¹ cm⁻² Å⁻¹)")
    fig.suptitle("Euclid NISP combined spectra")
    fig.supxlabel("Dotted lines show SPE-predicted wavelengths · × marks a mask-2 bin")
    fig.savefig(output / "Euclid_pair_spectra.png", dpi=155)
    plt.close(fig)
    pd.DataFrame(rows).to_csv(output / "spectral_fits.csv", index=False, float_format="%.9g")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PAIR)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = PAIR / "inputs"
    targets, positions = read_targets(inputs)
    targets["invalid_vis_pixels_within_1arcsec"] = plot_images(inputs, args.output, positions)
    measure_lines(inputs, args.output, targets)
    targets.to_csv(args.output / "source_matches.csv", index=False, float_format="%.12g")
    separation = float(positions[0].separation(positions[1]).arcsec)
    (args.output / "pair_geometry.json").write_text(json.dumps({
        "separation_arcsec": separation, "tile": TILE, "cosmology": "Planck18"
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
