"""Estimate a within-tile VIS radius contrast with documented red-grism fluxes."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_spe_line_quality import best_per_source, read_lines, valid_flux_rows
from audit_vis_apertures import DAY02
from analyse_day01 import ZRANGES, cell_stat

SEED = 20261115
DRAWS = 4000
MIN_PER_HALF = 5


def tile_size_cells(tile):
    """Keep cells with at least five objects in each Hα half."""
    cells = []
    for iz, (low, high) in enumerate(ZRANGES):
        redshift = tile.spe_z.between(low, high, inclusive="left")
        subset = tile[redshift].copy()
        subset["vis_half"] = subset.flux_vis_2fwhm_aper.gt(subset.flux_vis_2fwhm_aper.median())
        for bright, cell in subset.groupby("vis_half"):
            high_ha = cell.ha_flux.gt(cell.ha_flux.median()).to_numpy()
            if min(high_ha.sum(), (~high_ha).sum()) >= MIN_PER_HALF:
                cells.append((iz, bool(bright), cell.log_radius.to_numpy(), high_ha))
    return cells


def tile_sign_test(effects, weights):
    """Enumerate a tile sign-flip diagnostic under symmetric, independent tile errors."""
    observed = np.average(effects, weights=weights)
    signed = np.array(list(itertools.product((-1, 1), repeat=len(effects))))
    null = signed @ (effects * weights) / weights.sum()
    return float(np.mean(np.abs(null) >= abs(observed) - 1e-15))


def analyse(sample):
    rng = np.random.default_rng(SEED)
    tile_rows = []
    within_cells = []
    for tile_id, tile in sample.groupby("tileid"):
        cells = tile_size_cells(tile)
        totals = sum(len(x) for _, _, x, _ in cells)
        effect = (float(np.average(
            [cell_stat(x, high) for _, _, x, high in cells],
            weights=[len(x) for _, _, x, _ in cells],
        )) if totals else None)
        tile_rows.append({"tileid": int(tile_id), "n_selected": len(tile),
                          "n_in_cells": totals, "cells": len(cells), "effect_dex": effect})
        within_cells.extend(cells)
    good = [row for row in tile_rows if row["n_in_cells"]]
    if len(good) < 2:
        return {"n_selected": len(sample), "tiles": tile_rows, "status": "insufficient_tiles"}
    effect = np.array([row["effect_dex"] for row in good])
    weights = np.array([row["n_in_cells"] for row in good])
    bootstrap_tiles = rng.integers(len(good), size=(DRAWS, len(good)))
    blocks = np.average(effect[bootstrap_tiles], weights=weights[bootstrap_tiles], axis=1)
    estimate = float(np.average(effect, weights=weights))
    permutation = np.empty(DRAWS)
    sizes = [len(x) for _, _, x, _ in within_cells]
    for i in range(DRAWS):
        permutation[i] = np.average(
            [cell_stat(x, rng.permutation(high)) for _, _, x, high in within_cells],
            weights=sizes,
        )
    return {
        "n_selected": len(sample), "n_in_cells": int(weights.sum()), "tiles": tile_rows,
        "pooled_within_tile_dex": estimate,
        "within_cell_label_permutation_p": float(
            (1 + np.count_nonzero(abs(permutation) >= abs(estimate))) / (DRAWS + 1)
        ),
        "tile_sign_flip_p": tile_sign_test(effect, weights),
        "tile_bootstrap_percentiles_dex": np.quantile(blocks, [0.025, 0.975]).tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line-cache", type=Path, required=True)
    args = parser.parse_args()
    clean = pd.read_csv(DAY02 / "observed_results" / "strict_clean.csv")
    images = pd.read_csv(DAY02 / "joint_audit" / "vis_growth_curves.csv.gz")
    frame = clean.merge(images, on=["object_id", "tileid"], validate="one_to_one")
    if len(frame) != len(clean):
        raise ValueError("VIS coverage differs from the strict imaging catalogue")
    lines = valid_flux_rows(read_lines(args.line_cache))
    red, ambiguous = best_per_source(lines[lines.object_id.isin(frame.object_id)], (212,))
    red = red[["object_id", "spe_line_flux_gf"]].rename(columns={"spe_line_flux_gf": "red_flux"})
    frame = frame.merge(red, on="object_id", validate="one_to_one").sort_values("object_id")
    frame = frame[frame.image_status.eq("measured") & frame.nominal_aperture_snr_1p5arcsec.ge(15)
                  & frame[["r50_1arcsec", "r50_1p5arcsec", "r50_2arcsec"]].gt(0).all(axis=1)]
    frame["log_radius"] = np.log10(frame.r50_1p5arcsec)
    output = {"seed": SEED, "draws": DRAWS, "ambiguous_red_fits": ambiguous,
              "minimum_objects_per_halpha_half": MIN_PER_HALF, "selections": {}}
    for cut in (2.0, 2.5):
        sample = frame[frame.neighbour_arcsec.ge(cut)]
        output["selections"][str(cut)] = {
            "day02_median": analyse(sample),
            "reliable_red": analyse(sample.assign(ha_flux=sample.red_flux)),
        }
    path = DAY02 / "validation" / "vis_spatial_blocks.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    for cut, choices in output["selections"].items():
        for key, row in choices.items():
            print(cut, key, {k: v for k, v in row.items() if k != "tiles"}, flush=True)


if __name__ == "__main__":
    main()
