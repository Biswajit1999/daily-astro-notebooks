"""Compare NISP-J recurrence across separation bins within VIS rank strata."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


SCORE_EDGES = (8, 10, 15, 25, 50)
RATIO_EDGES = (0.4, 0.6, 0.8)
TESTABLE = {"no_repeat", "no_local_peak", "pass"}
COHORTS = ("pilot", "holdout")


def freeze_inputs(pilot, holdout, output):
    columns = [[] for _ in range(6)]
    for index, path in enumerate((pilot, holdout)):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row["j_state"] not in TESTABLE:
                    continue
                values = (
                    index, int(row["tile"]), float(row["sep_arcsec"]),
                    min(float(row["vis_score1"]), float(row["vis_score2"])),
                    float(row["vis_peak_ratio"]), int(row["j_state"] == "pass"),
                )
                for col, value in zip(columns, values, strict=True):
                    col.append(value)
    np.savez_compressed(output, cohort=np.asarray(columns[0], dtype=np.uint8),
                        tile=np.asarray(columns[1], dtype=np.int32),
                        separation=np.asarray(columns[2], dtype=np.float64),
                        score=np.asarray(columns[3], dtype=np.float64),
                        ratio=np.asarray(columns[4], dtype=np.float64),
                        passed=np.asarray(columns[5], dtype=np.uint8))


def strata(data, selection, score_edges, ratio_edges):
    observed = data["separation"]
    short = selection & (observed >= .38) & (observed < .50)
    long = selection & (observed >= .86) & (observed <= .950001)
    score = np.digitize(data["score"], score_edges)
    ratio = np.digitize(data["ratio"], ratio_edges)
    tile_ids = np.unique(data["tile"][selection])
    cube = np.zeros((len(tile_ids), len(score_edges)+1, len(ratio_edges)+1, 2, 2))
    for idx, tile in enumerate(tile_ids):
        for group, chosen in enumerate((short, long)):
            use = chosen & (data["tile"] == tile)
            np.add.at(cube[idx, :, :, group, 0], (score[use], ratio[use]), 1)
            np.add.at(cube[idx, :, :, group, 1], (score[use], ratio[use]), data["passed"][use])
    return tile_ids, cube


def tile_terms(cube):
    short = cube[..., 0, 0]
    long = cube[..., 1, 0]
    valid = (short > 0) & (long > 0)
    weight = np.divide(short * long, short + long, out=np.zeros_like(short), where=valid)
    low = np.divide(cube[..., 0, 1], short, out=np.zeros_like(short), where=valid)
    high = np.divide(cube[..., 1, 1], long, out=np.zeros_like(long), where=valid)
    sums = np.column_stack((weight.sum(axis=(1, 2)), (weight*low).sum(axis=(1, 2)),
                            (weight*high).sum(axis=(1, 2))))
    return sums, valid


def contrast(terms):
    weight, low, high = terms.sum(axis=0)
    return (high-low)/weight if weight > 0 else np.nan


def fit(data, selection, score_edges=SCORE_EDGES, ratio_edges=RATIO_EDGES):
    tile_ids, cube = strata(data, selection, score_edges, ratio_edges)
    terms, valid = tile_terms(cube)
    totals = cube.sum(axis=(0, 1, 2))
    support = np.sum(cube[valid], axis=0)
    weight, low, high = terms.sum(axis=0)
    if not weight:
        raise ValueError("No brightness and contrast-ratio stratum contains both separations.")
    rng = np.random.default_rng(180611)
    boot = terms[rng.integers(0, len(terms), size=(10000, len(terms)))].sum(axis=1)
    boot = boot[boot[:, 0] > 0]
    ci = np.quantile((boot[:, 2]-boot[:, 1])/boot[:, 0], [.025, .975])
    leave_one = np.array([contrast(np.delete(terms, i, axis=0)) for i in range(len(terms))])
    single = [(int(tile), contrast(terms[i:i+1])) for i, tile in enumerate(tile_ids)]
    return {
        "tiles": len(terms), "overlap_strata": int(valid.sum()),
        "narrow": {"tested": int(totals[0, 0]), "pass": int(totals[0, 1]),
                   "supported": int(support[0, 0]), "adjusted": float(low/weight)},
        "wide": {"tested": int(totals[1, 0]), "pass": int(totals[1, 1]),
                 "supported": int(support[1, 0]), "adjusted": float(high/weight)},
        "adjusted_difference": float((high-low)/weight), "tile_bootstrap_95": ci.tolist(),
        "leave_one_tile_out_range": [float(np.nanmin(leave_one)), float(np.nanmax(leave_one))],
        "individual_tile_difference": {tile: float(v) if np.isfinite(v) else None for tile, v in single},
    }


def study(path):
    with np.load(path, allow_pickle=False) as table:
        data = dict(table)
    return {
        name: {
            "primary": fit(data, data["cohort"] == i),
            "coarser": fit(data, data["cohort"] == i, (10, 20), (0.5,)),
            "tile_only": fit(data, data["cohort"] == i, (), ()),
        }
        for i, name in enumerate(COHORTS)
    }


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    freeze_inputs(args.pilot, args.holdout, args.inputs)
    args.output.write_text(json.dumps(study(args.inputs), indent=2, allow_nan=False)+"\n")
