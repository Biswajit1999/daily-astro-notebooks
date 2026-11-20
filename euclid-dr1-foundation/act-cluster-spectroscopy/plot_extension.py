"""Plot the area and galaxy counts for the extended spectroscopic sample."""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parent


def plot(pilot, extension, output):
    previous = json.loads(pilot.read_text())["measured_fields"]
    followup = json.loads(extension.read_text())["fields"]
    fields = sorted(previous + followup, key=lambda f: (-f["outskirts_candidates"], f["act_name"]))
    labels = [f["act_name"].removeprefix("ACT-CL ").replace("-", "−") for f in fields]
    ys = np.arange(len(fields))
    optical_colour, near_ir_colour, matched_colour = "#0072B2", "#D55E00", "#565656"
    fig, (area, count) = plt.subplots(1, 2, figsize=(9.5, 6.2), sharey=True)
    for i, f in enumerate(fields):
        optical, common = (100 * f["area"][k] for k in ("optical_fraction", "common_fraction"))
        area.plot([common, optical], [i, i], color=".8", lw=1)
        area.scatter(optical, i - .13, color=optical_colour, marker="o", s=20, zorder=2)
        area.scatter(common, i + .13, color=near_ir_colour, marker="s", s=18, zorder=3)
        n = [f["unique_mer_matches"], f["tallies"]["optical"]["count"],
             f["tallies"]["common_footprint"]["count"]]
        count.plot([min(n), max(n)], [i, i], color=".8", lw=1)
        for x, dy, colour, marker in zip(
            n, (-.20, 0, .20), (matched_colour, optical_colour, near_ir_colour), ("d", "o", "s"), strict=True
        ):
            count.scatter(x, i + dy, color=colour, marker=marker, s=19, zorder=2)
        if common == 0:
            area.text(5, i + .13, "Zero $J$ coverage", fontsize=8, va="center")
    area.set_yticks(ys, labels, fontsize=9)
    area.invert_yaxis()
    area.set(xlim=(-3, 103), xlabel="Annular area passing selection (%)", title="a  |  Area")
    count.set(xlim=(-.45, 9.55), xlabel="Distinct spectroscopic galaxies", title="b  |  Galaxy counts")
    count.set_xticks(np.arange(0, 10, 1))
    count.tick_params(axis="y", left=False, labelleft=False)
    for ax in (area, count):
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=".9", lw=.75)
        ax.set_axisbelow(True)
    legend = [
        Line2D([], [], marker="d", color=matched_colour, ls="", ms=5, label="Registered counterpart"),
        Line2D([], [], marker="o", color=optical_colour, ls="", ms=5, label="Strict optical"),
        Line2D([], [], marker="s", color=near_ir_colour, ls="", ms=5, label="Shared optical + J footprint"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, bbox_to_anchor=(.54, .055),
               fontsize=9, frameon=False)
    fig.suptitle("Euclid coverage and spectroscopic members of ACT clusters", fontsize=15,
                 fontweight="semibold", y=.967)
    fig.text(.54, .029, "1–2 R₅₀₀ annuli · ACT, SPT-GMOS and Euclid DR1-Foundation · Biswajit Jana",
             ha="center", fontsize=8.5, color=".3")
    fig.subplots_adjust(left=.20, right=.97, bottom=.18, top=.87, wspace=.2)
    fig.savefig(output, dpi=185, bbox_inches="tight", pad_inches=.14)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=ROOT / "results/spectroscopy_results.json")
    parser.add_argument("--extension", type=Path, default=ROOT / "results/extended_sample.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/extended_sample.png")
    args = parser.parse_args()
    plot(args.pilot, args.extension, args.output)
