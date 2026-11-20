"""Measure VIS-H central colours and render a false-colour atlas of six dwarfs."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.wcs import WCS
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.stats import median_abs_deviation

HERE = Path(__file__).resolve().parent
PIX = 0.1
SIDE = 321
RADII = (0.8, 1.5, 3.0)
SKY_RINGS = ((5.0, 7.0), (7.0, 9.0))
COMMON_FWHM = (0.70, 0.95)
PSF_SHIFTS = ((0., 0.), (0.05, -0.05), (-0.05, 0.05))
BANDS = ("VIS", "NIR-Y", "NIR-H")
HALF_SIDE = (SIDE-1) / 2
Y, X = (np.indices((SIDE, SIDE), dtype=float) - HALF_SIDE) * PIX
R = np.hypot(X, Y)
QUADRANT = np.floor((np.arctan2(Y, X)+2*np.pi) % (2*np.pi)/(np.pi/2)).astype(int)


def apertures(r):
    return r <= RADII[0], (r > RADII[1]) & (r <= RADII[2])


def reprojection(cutout, target):
    grid = WCS(naxis=2)
    grid.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    grid.wcs.crval = [target["ra"], target["dec"]]
    grid.wcs.crpix = [HALF_SIDE+1, HALF_SIDE+1]
    grid.wcs.cdelt = [-PIX/3600, PIX/3600]

    ra, dec = grid.pixel_to_world_values(X/PIX + HALF_SIDE, Y/PIX + HALF_SIDE)
    output = []
    with np.load(cutout) as data:
        for band in BANDS:
            h = fits.Header.fromstring(str(data[f"{band}_header"]), sep="\n")
            x, y = WCS(h).world_to_pixel_values(ra, dec)
            plane = map_coordinates(data[band], [y, x], order=1, cval=np.nan)
            if not np.all(np.isfinite(plane)) or np.any((plane == 0) & (R < 9.0)):
                raise ValueError(f"Invalid image values near {target['object_id']} in {band}")
            output.append(plane.astype(float) * 10**((25.0-h["MAGZERO"])/2.5))
    return output


def smooth(plane, native, target):
    if not 0 < native < target:
        raise ValueError(f"Cannot match FWHM {native} arcsec to {target} arcsec")
    sigma = np.sqrt(target**2-native**2)/(PIX*np.sqrt(8*np.log(2)))
    return gaussian_filter(plane, sigma)


def sky_level(plane, ring):
    return float(np.ma.median(sigma_clip(plane[(R >= ring[0]) & (R < ring[1])],
                                        sigma=3.0, maxiters=4)))


def aperture_fluxes(planes, masks, levels):
    return np.array([[(plane[mask]-level).sum() for mask in masks]
                     for plane, level in zip(planes, levels)])


def colour_difference(fluxes):
    if np.min(fluxes) <= 0:
        raise ValueError("Positive net flux is required in both bands and apertures")
    (vi, vo), (hi, ho) = fluxes
    return float(-2.5*np.log10((vi/hi)/(vo/ho)))


def empirical_uncertainty(planes, fluxes):
    """Linearised colour scatter from translated aperture fluxes and covariance."""
    trials = []
    for angle in np.arange(12)*2*np.pi/12:
        shifted_r = np.hypot(X-12*np.cos(angle), Y-12*np.sin(angle))
        trials.append(aperture_fluxes(planes, apertures(shifted_r), (0., 0.)))
    trials = np.array(trials)
    typical = np.median(trials, axis=0)
    scale = median_abs_deviation(trials, axis=0, scale="normal")
    if np.any(scale <= 0):
        return None, 0
    accepted = np.all(np.abs(trials-typical) < 3.5*scale, axis=(1, 2))
    used = int(accepted.sum())
    if used < 6:
        return None, used
    derivative = (-2.5/np.log(10)) * np.array([[1., -1.], [-1., 1.]])/fluxes
    projected = np.sum((trials[accepted]-typical)*derivative, axis=(1, 2))
    return float(median_abs_deviation(projected, scale="normal")), used


def measure(planes, psf):
    settings = []
    leave_one_quadrant_out = []
    for common in COMMON_FWHM:
        for shift_v, shift_h in PSF_SHIFTS:
            pair = [smooth(planes[0], psf[0]+shift_v, common),
                    smooth(planes[2], psf[2]+shift_h, common)]
            for ring in SKY_RINGS:
                levels = [sky_level(plane, ring) for plane in pair]
                fluxes = aperture_fluxes(pair, apertures(R), levels)
                settings.append({
                    "common_fwhm_arcsec": common,
                    "psf_fwhm_shifts_vis_h_arcsec": [shift_v, shift_h],
                    "sky_ring_arcsec": list(ring),
                    "delta_vis_minus_h_mag": colour_difference(fluxes),
                    "flux_inner_outer_vis_h_zp25": fluxes.tolist(),
                    "sky_vis_h_zp25": levels,
                })
                if len(settings) == 1:
                    scatter, used = empirical_uncertainty(pair, fluxes)
                    inner, annulus = apertures(R)
                    for quadrant in range(4):
                        fluxes_without_quadrant = aperture_fluxes(pair, (inner, annulus & (QUADRANT != quadrant)),
                                                                 levels)
                        leave_one_quadrant_out.append(colour_difference(fluxes_without_quadrant))
    values = [setting["delta_vis_minus_h_mag"] for setting in settings]
    display = [smooth(plane, width, COMMON_FWHM[0]) for plane, width in zip(planes, psf)]
    display = np.stack([plane - sky_level(plane, SKY_RINGS[0]) for plane in display[::-1]], axis=-1)
    return {
        "baseline_mag": values[0], "sensitivity_min_mag": min(values),
        "sensitivity_max_mag": max(values), "background_scatter_mag": scatter,
        "background_apertures_used": used,
        "leave_one_outer_quadrant_out_mag": leave_one_quadrant_out, "settings": settings,
    }, display


def plot_atlas(samples, images, native_vis=False):
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 7.8))
    fig.subplots_adjust(left=.083, right=.984, bottom=.09, top=.852, hspace=.14, wspace=.08)
    title = "Euclid optical detail at native VIS resolution" if native_vis else "Dwarf galaxies in Euclid Deep Field North"
    fig.text(.083, .946, title, weight="bold", size=18)
    subtitle = ("Euclid Deep Field North  ·  VIS  ·  photometry apertures drawn on each panel"
                if native_vis else "DR1-Foundation imaging  ·  false colour  ·  H → red, Y → green, VIS → blue")
    fig.text(.083, .909, subtitle, size=10)
    radius = 6.0
    semisize = int(radius/PIX)
    centre = int(HALF_SIDE)
    cut = slice(centre-semisize, centre+semisize+1)
    frames = np.asarray(images)[:,cut,cut].clip(0)
    brightness = frames if native_vis else frames.mean(axis=-1)
    high = np.quantile(brightness, .995)
    stretched = np.arcsinh(12*brightness/high)/np.arcsinh(12)
    if native_vis:
        display = stretched.clip(0, 1)
    else:
        factor = np.divide(stretched, brightness, out=np.zeros_like(stretched), where=brightness > 0)
        display = frames*factor[...,None]
        display /= np.maximum(1., display.max(axis=-1, keepdims=True))
    for index, (sample, frame) in enumerate(zip(samples, display)):
        row, column = index % 2, index // 2
        ax = axes[row, column]
        extent = radius+PIX/2
        ax.imshow(frame, origin="lower", extent=(-extent, extent, -extent, extent),
                  interpolation="nearest", rasterized=True, cmap="gray", vmin=0, vmax=1)
        ax.set_axis_off()
        ax.text(.048, .94, ("A", "B", "C")[column]+("1" if row == 0 else "2"),
                weight="bold", color="white", va="top", transform=ax.transAxes)
        ax.text(.048, .05, sample["object_id"], color="white", size=6.6, transform=ax.transAxes)
        if native_vis:
            for r in RADII:
                ax.add_patch(plt.Circle((0, 0), r, edgecolor="#72d7e8", fill=False, lw=.7, alpha=.9))
        if index == 0:
            ax.plot([3.2, 5.2], [-4.9, -4.9], color="white", lw=1)
            ax.text(4.2, -4.65, "2″", color="white", ha="center", size=8)
            arrows = {"arrowstyle": "->", "color": "white", "lw": 0.65}
            ax.annotate("", xy=(4.85, 4.90), xytext=(4.85, 3.72), arrowprops=arrows)
            ax.annotate("", xy=(3.65, 3.72), xytext=(4.85, 3.72), arrowprops=arrows)
            ax.text(4.85, 5.00, "N", ha="center", color="white", size=7)
            ax.text(3.37, 3.67, "E", ha="center", va="center", color="white", size=7)
    for row, label in enumerate(("Blue-core tag", "Matched control")):
        pos = axes[row, 0].get_position()
        fig.text(.041, (pos.y0+pos.y1)/2, label, rotation=90, va="center", ha="center", size=10)
    caption = ("VIS has been registered to a 0.1″ grid. The circles mark radii of 0.8″, 1.5″ and 3.0″."
               if native_vis else "Same stretch and approximate 0.70″ resolution in all panels. Each column is a matched pair.")
    fig.text(.083, .048, caption, size=9)
    fig.text(.083, .024, "Biswajit Jana  ·  Observations from ESA / Euclid / Euclid Consortium / NASA (IRSA)",
             size=8, color="#3d4a54")
    return fig


def plot_measurements(samples):
    fig, ax = plt.subplots(figsize=(10.2, 6.4))
    fig.subplots_adjust(left=.17, right=.959, top=.77, bottom=.25)
    fig.text(.10, .93, "Central colour differences in six dwarf candidates", weight="bold", size=17)
    fig.text(.10, .872, "Central aperture r ≤ 0.8″    ·    Outer annulus 1.5″ < r ≤ 3.0″", size=10)
    y = [5.5, 4.8, 3.55, 2.85, 1.6, .9]
    for index, (sample, row) in enumerate(zip(samples, y)):
        result = sample["result"]
        colour = "#155f81" if sample["blue"] else "#a24e2d"
        base = result["baseline_mag"]
        ax.hlines(row, result["sensitivity_min_mag"], result["sensitivity_max_mag"],
                  color=colour, lw=8, alpha=.22, zorder=2)
        ax.errorbar(base, row, xerr=result["background_scatter_mag"], fmt="o" if sample["blue"] else "s",
                    color=colour, capsize=4, lw=1.3, markersize=5, zorder=3)
    ax.axvline(0., lw=.8, color="#32383f", linestyle="--")
    ax.set_ylim(.3, 6.1)
    ax.set_yticks(y, ["A1  Tagged", "A2  Control", "B1  Tagged", "B2  Control", "C1  Tagged", "C2  Control"])
    ax.set_xlabel(r"$\Delta$(VIS − $H$) = centre minus annulus [mag]", labelpad=11)
    ax.grid(axis="x", alpha=.16)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=9)
    fig.text(.10, .130, "Negative values indicate a bluer centre. Capped lines show approximate local background scatter.",
             size=9)
    fig.text(.10, .093, "Shaded ranges span 12 combinations of smoothing, PSF-width shifts and sky annuli.",
             size=9)
    near = samples[4]["result"]["leave_one_outer_quadrant_out_mag"]
    fig.text(.10, .056, f"Omitting one outer quadrant at a time gives {min(near):.2f} to {max(near):.2f} mag for C1.",
             size=9)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    psfs = json.loads((HERE / "psf_inputs.json").read_text())
    samples, rgb, vis = [], [], []
    for pair in json.loads((HERE / "targets.json").read_text()):
        for target in pair:
            object_id = target["object_id"]
            planes = reprojection(args.cache / f"{object_id}.npz", target)
            widths = [psfs[object_id][band]["central_stamp_fwhm_arcsec"] for band in BANDS]
            result, display = measure(planes, widths)
            samples.append({**target, "result": result})
            rgb.append(display)
            vis.append(planes[0]-sky_level(planes[0], SKY_RINGS[0]))
    (args.output / "colour_measurements.json").write_text(json.dumps(samples, indent=2) + "\n")
    atlas, detail, plot = plot_atlas(samples, rgb), plot_atlas(samples, vis, native_vis=True), plot_measurements(samples)
    with PdfPages(args.output / "Euclid_EDF_North_Dwarf_Colours.pdf",
                  metadata={"Author": "Biswajit Jana", "Title": "Dwarf galaxy colours in Euclid Deep Field North",
                            "CreationDate": None}) as pdf:
        pdf.savefig(atlas, dpi=165)
        pdf.savefig(detail, dpi=165)
        pdf.savefig(plot)
    plt.close("all")


if __name__ == "__main__":
    main()
