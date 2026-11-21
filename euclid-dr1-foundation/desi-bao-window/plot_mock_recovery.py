"""Plot the paired Abacus mock recovery comparison."""
from argparse import ArgumentParser
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mock_recovery import CENTRES, HERE, PEAK_GRID, PRIMARY, regressions

COLOURS = ("#28606b", "#c25b3f", "#734b84")
GROUPS = ("Full DESI window", "Euclid overlap", "Overlap at observed count")
SHORT = ("Full DESI", "Overlap", "Count-matched")


def plot(path, output):
    doc = json.loads(path.read_text())
    results, summary, windows = doc["results"], doc["summary"], doc["windows"]
    xi = np.array([[r["windows"][w]["xi"] for r in results] for w in windows])
    residuals = xi@regressions()[0]
    primary = np.array(summary["primary_amplitude_by_window_then_mock"])
    means = np.array(summary["fixed_template_means"])[:3, 0]
    bounds = np.array(summary["fixed_template_bootstrap_95_pct"])[:, :3, 0]
    pos = np.array(summary["free_peak_by_window_then_mock_h_inv_mpc"], dtype=float)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.9))
    fig.subplots_adjust(left=.097, right=.971, top=.855, bottom=.177, hspace=.64, wspace=.33)
    fig.text(.097, .956, "Can the Euclid–DESI overlap recover the acoustic peak?",
             fontsize=19, weight="bold", color="#172b32")
    fig.text(.097, .914, f"{len(results)} matched AbacusSummit realisations  ·  DESI DR1 LRG mocks  ·  Biswajit Jana",
             fontsize=10.5, color="#3b5159")
    for ax, inds, title in ((axes[0, 0], (0,), "Full DESI window (thinned)"),
                            (axes[0, 1], (1, 2), "Euclid overlap")):
        ax.set_title(title, loc="left", weight="bold", pad=10)
        ax.axvline(PRIMARY[0], color="#8b989e", linestyle="--", linewidth=1.)
        for i in inds:
            mean = residuals[i].mean(axis=0)
            se = residuals[i].std(axis=0, ddof=1)/np.sqrt(len(results))
            shift = .9 if i == 2 else 0.
            ax.errorbar(CENTRES+shift, 1000*mean, yerr=1000*se, color=COLOURS[i], lw=1.4,
                        label="Observed count (thinned)" if i == 2 else GROUPS[i], marker="o", ms=3.4, capsize=2)
        ax.set_ylabel(r"Residual $\xi(s)$ [$10^{-3}$]")
        ax.set_xlabel(r"Separation [$h^{-1}$ Mpc]")
        ax.set_xlim(48, 152)
        ax.axhline(0, color="#62737b", lw=.65)
        if len(inds) > 1:
            ax.legend(frameon=False, fontsize=8.1)

    ax = axes[1, 0]
    for col in primary.T:
        ax.plot(np.arange(3), 1000*col, color="#b3bdc0", lw=.7, zorder=1)
    for i, colour in enumerate(COLOURS):
        ax.scatter(np.full(len(results), i), 1000*primary[i], color=colour, alpha=.55, s=19, zorder=2)
        ax.errorbar(i+.13, 1000*means[i], yerr=1000*np.array([[means[i]-bounds[0,i]],
                                                            [bounds[1,i]-means[i]]]),
                    color=colour, marker="D", ms=5.2, capsize=4, zorder=3)
    ax.set_title("Fixed-location acoustic contrast", loc="left", weight="bold", pad=10)
    ax.set_ylabel(r"Fitted bump amplitude [$10^{-3}$]")
    ax.axhline(0, color="#65777e", lw=.7)

    ax = axes[1, 1]
    ax.axhline(PRIMARY[0], color="#8b989e", linestyle="--", linewidth=1.)
    ax.axhline(PEAK_GRID[0], color="#a7aeb1", linestyle=":", linewidth=.85)
    ax.axhline(PEAK_GRID[-1], color="#a7aeb1", linestyle=":", linewidth=.85)
    offset = np.linspace(-.13, .13, len(results))
    for i, colour in enumerate(COLOURS):
        ax.scatter(i+offset, pos[i], color=colour, s=27)
    ax.set_title("Best-fit locations in individual mocks", loc="left", weight="bold", pad=10)
    ax.set_ylabel(r"Bump centre [$h^{-1}$ Mpc]")
    ax.set_ylim(81, 127)
    for ax in axes[1]:
        ax.set_xticks(range(3), SHORT)
        ax.set_xlim(-.42, 2.43)
        ax.grid(axis="y", alpha=.17)
    fig.text(.097, .093, "Top panels show mean residuals and the standard error across mocks. Their vertical scales differ.",
             fontsize=9.3, color="#3b5159")
    fig.text(.097, .062, "Diamonds show mean fixed-centre amplitudes with 95% bootstrap intervals. Dotted lines bound the peak scan.",
             fontsize=9.3, color="#3b5159")
    fig.text(.097, .031, "One count-matched mock lacks a positive bump, so it has no best-fit location.",
             fontsize=9.3, color="#3b5159")
    fig.savefig(output, dpi=148)
    plt.close(fig)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE/"results"/"mock_recovery.json")
    parser.add_argument("--output", type=Path, default=HERE/"results"/"mock_recovery.png")
    args = parser.parse_args()
    plot(args.input, args.output)
