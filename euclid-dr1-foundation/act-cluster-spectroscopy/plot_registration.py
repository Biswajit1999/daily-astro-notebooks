"""Plot the spectroscopic astrometric shifts and sample counts."""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

RESULT = Path(__file__).resolve().parent / "results/spectroscopy_results.json"


def plot(source, output):
    data = json.loads(source.read_text())["measured_fields"]
    colors = ["#0072B2", "#D55E00", "#009E73"]
    tags = [field["act_name"].removeprefix("ACT-CL ") for field in data]
    fig, (shift, count) = plt.subplots(1, 2, figsize=(10.6, 4.6),
                                      gridspec_kw={"width_ratios": [1, 1.4]})
    for idx, (field, col, tag) in enumerate(zip(data, colors, tags, strict=True)):
        for k, row in enumerate(field["slit_mask_offsets"].values()):
            offset = (row["east_arcsec"], row["north_arcsec"])
            radius = row["leave_one_out_rms_arcsec"]
            shift.add_patch(Circle(offset, radius, edgecolor=col, facecolor="none", alpha=.62, lw=1))
            shift.plot(*offset, marker=("o", "s")[k], color=col, ms=6,
                       markerfacecolor=col if k == 0 else "white", label=tag if k == 0 else None)
        steps = [
            field["unique_matches_before_registration"], field["spectra_with_unique_mer_match"],
            field["unique_mer_matches"], field["tallies"]["optical"]["count"],
            field["tallies"]["common_footprint"]["count"],
        ]
        x = np.arange(len(steps)) + .22 * (idx - 1)
        count.bar(x, steps, width=.195, color=col)
        for xval, n in zip(x, steps, strict=True):
            count.text(xval, n + .16, str(n), ha="center", va="bottom", fontsize=8, color=col)
    shift.axvline(0, color=".78", lw=.8)
    shift.axhline(0, color=".78", lw=.8)
    shift.set(xlim=(-1.95, 2.05), ylim=(-1.85, 4.3), xlabel="Correction east (arcsec)",
              ylabel="Correction north (arcsec)", title="a  |  Shift fitted in each slit mask")
    shift.set_aspect("equal")
    count.set_xticks(range(5), ["Raw\npositions", "Registered\npositions", "Unique\ngalaxies",
                               "Optical\nquality cuts", "Shared\nfootprint"], fontsize=8.5)
    count.set(xlim=(-.52, 4.52), ylim=(0, 11.2), ylabel="Count",
              title="b  |  Matches and sample cuts in the outskirts")
    count.set_yticks(range(0, 11, 2))
    count.grid(axis="y", color=".89", lw=.7)
    count.set_axisbelow(True)
    for ax in (shift, count):
        ax.spines[["top", "right"]].set_visible(False)
    handles, names = shift.get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", bbox_to_anchor=(.52, .067),
               ncol=3, frameon=False, fontsize=9)
    fig.suptitle("Gemini spectroscopy matched to Euclid cluster photometry",
                 fontsize=15, weight="semibold")
    fig.text(.51, .035, "ACT and SPT-GMOS clusters · Euclid DR1-Foundation · Biswajit Jana",
             ha="center", color=".27", fontsize=9)
    fig.subplots_adjust(left=.09, right=.96, top=.83, bottom=.245, wspace=.25)
    fig.savefig(output, dpi=190, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RESULT)
    parser.add_argument("--output", type=Path, default=RESULT.with_name("registration.png"))
    args = parser.parse_args()
    plot(args.input, args.output)
