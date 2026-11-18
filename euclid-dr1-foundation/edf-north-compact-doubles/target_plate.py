"""Create a matched-view plate from registered observed FITS cutouts."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audits = json.loads((args.results / "audit.json").read_text())
    checks = json.loads((args.results / "image_checks.json").read_text())["profiles"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": "#14212b"})
    fig, axes = plt.subplots(6, 3, figsize=(6.8, 11.2))
    fig.subplots_adjust(left=0.235, right=0.975, top=0.927, bottom=0.064,
                        wspace=0.038, hspace=0.045)
    fig.text(0.04, 0.977, "Six compact pairs in Euclid Deep Field North", size=15, weight="bold")
    fig.text(0.04, 0.955, "Observed imaging  •  North up, east left  •  Each panel is 5″ across", size=8.8)
    titles = ("Euclid VIS", "Euclid NISP J", "Subaru HSC i2")
    for ax, name in zip(axes[0], titles, strict=True):
        ax.set_title(name, fontsize=9.5, weight="bold", pad=8)
    for plot_row, (name, audit) in enumerate(audits.items()):
        row = audit["candidate"]
        path = args.results / "audit" / name / "registered.fits.gz"
        with fits.open(path, memmap=False) as hdus:
            wcs = WCS(hdus["VIS"].header).celestial
            x, y = wcs.world_to_pixel_values([row["ra1"], row["ra2"]], [row["dec1"], row["dec2"]])
            for i, (band, band_label) in enumerate(zip(("VIS", "J", "HSC_I2"),
                                                      ("VIS", "J", "HSC i2"), strict=True)):
                ax = axes[plot_row, i]
                data = hdus[band].data
                metrics = audit["images"][band_label]
                pix = (data - metrics["background"]) / metrics["pixel_mad_sigma"]
                display = np.arcsinh(pix / 1.5)
                ax.imshow(display, cmap="gray", origin="lower", interpolation="nearest",
                          vmin=-0.3, vmax=np.nanpercentile(display[54:107, 54:107], 99.3))
                ax.set(xlim=(55, 105), ylim=(55, 105), xticks=[], yticks=[])
                for xp, yp in zip(x, y, strict=True):
                    ax.plot([xp - 1.3, xp - 4.3], [yp, yp], color="#f6cb77", lw=.65)
                    ax.plot([xp + 1.3, xp + 4.3], [yp, yp], color="#f6cb77", lw=.65)
                if plot_row == 0 and i == 0:
                    ax.plot([60, 70], [60, 60], lw=1.5, color="white")
                    ax.text(65, 62, "1″", color="white", size=7, ha="center")
        center = np.mean([axes[plot_row, 0].get_position().y0, axes[plot_row, 0].get_position().y1])
        fig.text(0.045, center + .024, name, size=10, weight="bold")
        fig.text(0.045, center + .006, f"VIS separation {row['sep_arcsec']:.2f}″", size=7.4)
        dip = checks[name]["HSC_I2"].get("dip")
        label = f"Subaru dip {100*dip:.1f}%" if dip is not None else "Unresolved in Subaru"
        fig.text(0.045, center - .012, label, size=7.4)
    fig.text(.045, .033, "Gold ticks mark the VIS peak positions. Each panel uses its own display stretch.", size=7.5)
    fig.text(.045, .018, "Image data ESA/Euclid/Euclid Consortium/NASA and Subaru/WISHES, via IRSA MER.", size=7.3)
    fig.savefig(args.output, dpi=210)
    plt.close(fig)


if __name__ == "__main__":
    main()
