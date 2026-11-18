"""Run controlled two-source injections using observed Euclid J backgrounds."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from search_doubles import dog, j_check, robust


SEPARATIONS = (.40, .50, .60, .70, .80, .90)
RATIOS = (.50, 1.)
LEVELS = (5., 10., 20.)
WIDTH_SCALES = (.85, 1., 1.15)
TRIAL_DTYPE = [
    ("tile", "i4"), ("stamp", "u1"), ("phase_index", "u1"), ("kind", "U6"),
    ("sep", "f4"), ("ratio", "f4"), ("level", "f4"), ("width_scale", "f4"), ("passed", "?"),
]
HALF_SPAN = 32
GRID = np.mgrid[-HALF_SPAN:HALF_SPAN+1, -HALF_SPAN:HALF_SPAN+1].astype(float)


def response(profile, pos, scale):
    x, y = pos
    yy, xx = GRID
    source = map_coordinates(profile, [(yy-y)/scale+12, (xx-x)/scale+12], order=3,
                             mode="constant", cval=0.)
    source = np.maximum(source, 0)
    filt, _ = dog(source, 1.25, 3.5)
    return filt / filt.max()


def experiments(filename):
    tile = int(filename.stem.split("_")[-1])
    with np.load(filename, allow_pickle=False) as data:
        stamps, profile = data["stamps"], data["profile"]
    rng = np.random.default_rng(tile + 691136)
    rows = []
    for number, stamp in enumerate(stamps):
        background, valid = dog(stamp, 1.25, 3.5)
        xy = (stamp.shape[0]-1)//2
        local_y, local_x = np.mgrid[-xy:xy+1, -xy:xy+1]
        d = np.hypot(local_y, local_x)
        ann = (d >= 20) & (d <= 65)
        _, noise = robust(background[ann])
        region = slice(xy-HALF_SPAN, xy+HALF_SPAN+1)
        for phase in range(3):
            midpoint = rng.uniform(-.5, .5, 2)
            orientation = rng.uniform(0, 2*np.pi)
            direction = np.array([np.cos(orientation), np.sin(orientation)])
            for scale in WIDTH_SCALES:
                for sep in SEPARATIONS:
                    a = midpoint - direction * (sep/.1)/2
                    b = midpoint + direction * (sep/.1)/2
                    positions = (np.array([a[0], b[0]])+xy, np.array([a[1], b[1]])+xy)
                    r1 = response(profile, a, scale)
                    r2 = response(profile, b, scale)
                    # The detector acts on a linear difference of two Gaussian filters.
                    # Add the filtered profiles to the identically filtered sky cutout.
                    if scale == 1.:
                        empty = j_check(background, valid, positions)["state"] == "pass"
                        rows.append((tile, number, phase, "empty", sep, 0, 0, scale, empty))
                        altered = background.copy()
                        altered[region, region] += 20*noise*r1
                        one = j_check(altered, valid, positions)["state"] == "pass"
                        rows.append((tile, number, phase, "single", sep, 0, 20, scale, one))
                    for ratio in RATIOS:
                        composite = r1/ratio + r2
                        for level in LEVELS:
                            altered = background.copy()
                            altered[region, region] += level*noise*composite
                            passed = j_check(altered, valid, positions)["state"] == "pass"
                            rows.append((tile, number, phase, "double", sep, ratio, level, scale, passed))
    return np.array(rows, dtype=TRIAL_DTYPE)


def run(inputs, workers):
    files = sorted(inputs.glob("background_*.npz"))
    if len(files) != 6:
        raise ValueError(f"Expected six background files, found {len(files)}.")
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return np.concatenate(list(pool.map(experiments, files)))


def summarize(trials):
    def results(subset):
        return {"tested": int(len(subset)), "passed": int(subset["passed"].sum())}

    doubles = trials[trials["kind"] == "double"]
    baseline = doubles[np.isclose(doubles["width_scale"], 1)]
    fixed = baseline[np.isclose(baseline["level"], 10)]
    return {
        "totals": {kind: results(trials[trials["kind"] == kind])
                   for kind in ("double", "single", "empty")},
        "baseline": [
            {"sep": sep, "faint_level": level, "ratio": ratio,
             **results(baseline[np.isclose(baseline["sep"], sep) & np.isclose(baseline["level"], level)
                                & np.isclose(baseline["ratio"], ratio)])}
            for sep in SEPARATIONS for level in LEVELS for ratio in RATIOS
        ],
        "width_sensitivity": [
            {"sep": sep, "width_scale": scale,
             **results(doubles[np.isclose(doubles["sep"], sep) & np.isclose(doubles["width_scale"], scale)
                               & np.isclose(doubles["ratio"], .5) & np.isclose(doubles["level"], 10)])}
            for sep in SEPARATIONS for scale in WIDTH_SCALES
        ],
        "nominal_ten_by_tile": [
            {"tile": int(tile), "sep": sep,
             **results(fixed[(fixed["tile"] == tile) & np.isclose(fixed["sep"], sep)
                             & np.isclose(fixed["ratio"], .5)])}
            for tile in np.unique(trials["tile"]) for sep in SEPARATIONS
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    observed = run(args.inputs, args.workers)
    np.savez_compressed(args.output/"injection_trials.npz", trials=observed)
    (args.output/"injection_summary.json").write_text(json.dumps(summarize(observed), indent=2)+"\n")
