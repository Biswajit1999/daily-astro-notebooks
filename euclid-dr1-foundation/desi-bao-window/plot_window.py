"""Plot the two survey footprints and orientation-dependent random-pair retention."""
from argparse import ArgumentParser
import json
from pathlib import Path

from astropy_healpix import HEALPix
import matplotlib.pyplot as plt
import numpy as np

from analyse import CONTROL_KEYS, HERE, MASK_FILES, MOC, u


def pair_curve(zbin, key):
    curves = np.array([r["pairs"]["inside"][key]["conditional_partner_fraction"] for r in zbin["randoms"]])
    return curves.mean(axis=0), curves.min(axis=0), curves.max(axis=0)


def plot(cache, results, output):
    summary = json.loads((results/"window_measurements.json").read_text())
    counts = np.load(cache/"desi_random_nside256_nested_counts.npy")
    hp = HEALPix(nside=256, order="nested")
    longitude, latitude = hp.healpix_to_lonlat(np.arange(hp.npix))
    mer = MOC.from_fits(cache/MASK_FILES["mer_wide"]).contains_lonlat(longitude, latitude)
    x = -longitude.wrap_at(180*u.deg).rad
    y = latitude.rad

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": "#243139"})
    fig = plt.figure(figsize=(11.7, 8.4), facecolor="white")
    gs = fig.add_gridspec(2, 3, left=.085, bottom=.14, right=.962, top=.865,
                          height_ratios=(1.9, 1.05), wspace=.28, hspace=.32)
    fig.text(.085, .954, "How the Euclid footprint changes the DESI pair sample",
             size=20, weight="bold", color="#162329")
    fig.text(.085, .918, "Euclid DR1-Foundation × DESI DR1 luminous red galaxies  ·  Biswajit Jana", size=11.5)
    ax = fig.add_subplot(gs[0, :], projection="mollweide")
    desi = counts >= 5
    for flag, colour, label, alpha, size in (
            (desi & ~mer, "#aebcc7", "DESI LRG random support", .9, 1.6),
            (mer & ~desi, "#c4693e", "Euclid MER Wide Survey", .92, 2.1),
            (mer & desi, "#0b6177", "Shared sky", 1., 6.0)):
        ax.scatter(x[flag], y[flag], c=colour, label=label, alpha=alpha, s=size, linewidths=0)
    caps = summary["control_caps"]
    if caps:
        ra = np.array([v["ra_deg"] for v in caps.values()])
        dec = np.array([v["dec_deg"] for v in caps.values()])
        ax.scatter(-np.deg2rad((ra+180) % 360-180), np.deg2rad(dec), c="#35505a", s=37,
                   marker="+", label="Control centres", linewidths=1.3, zorder=3)
    ax.grid(color="#546775", lw=.35, alpha=.48)
    ax.set_xticklabels(["150°", "120°", "90°", "60°", "30°", "0°", "330°", "300°", "270°", "240°", "210°"],
                       size=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.01), ncol=4, frameon=False, fontsize=9)
    mu = (np.array(summary["mu_edges"][:-1])+summary["mu_edges"][1:])/2
    for index, zbin in enumerate(summary["bins"]):
        ax = fig.add_subplot(gs[1, index])
        controls = np.array([pair_curve(zbin, key)[0] for key in CONTROL_KEYS])
        ax.fill_between(mu, 100*controls.min(axis=0), 100*controls.max(axis=0), color="#657b86", alpha=.2)
        ax.plot(mu, 100*np.median(controls, axis=0), color="#657b86", linestyle="--", linewidth=1.2,
                label="Equal-area cap controls")
        for key, colour, marker, label in (
                ("mer_wide", "#0b6177", "o", "MER Wide Survey"),
                ("wide_tiles", "#bc542a", "s", "Wide tiles")):
            centre, low, high = pair_curve(zbin, key)
            ax.fill_between(mu, 100*low, 100*high, color=colour, alpha=.18)
            ax.plot(mu, 100*centre, color=colour, marker=marker, markersize=4., lw=1.25, label=label)
        lo, hi = zbin["z"]
        ax.set_title(f"${lo:.1f} \\leq z < {hi:.1f}$", size=11)
        ax.set_ylim(0, 100)
        ax.set_xlim(0, 1)
        ax.set_xticks([.1, .5, .9])
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.grid(axis="y", alpha=.18)
        if index == 0:
            ax.set_ylabel("Partner also inside region [%]")
        if index == 1:
            ax.set_xlabel(r"$|\mu|$ to the line of sight   ·   0 across the sky, 1 along the line of sight")
        if index == 2:
            ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.text(.085, .059, "Weighted DESI random pairs at 95–115 h⁻¹ Mpc, given one endpoint inside the region.",
             size=9.4)
    fig.text(.085, .033, "Coloured bands span two thinnings. The grey band spans three area-matched circular regions.",
             size=9.4, color="#3f525c")
    fig.savefig(output, dpi=146)
    plt.close(fig)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=HERE/"results")
    args = parser.parse_args()
    plot(args.cache, args.results, args.results/"euclid_desi_window.png")
