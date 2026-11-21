"""Compare pre-reconstruction acoustic-bump fits on paired Abacus mock windows."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from analyse import CAPS, COSMOLOGY, HERE, MASK_FILES
from fetch_mocks import FULL_KEEP, MOCKS, SEED, Z

EDGES = np.arange(48., 153., 8.)
CENTRES = (EDGES[:-1]+EDGES[1:])/2
PEAK_GRID = np.arange(84., 124.01, .25)
PRIMARY = (104., 10.)
FIXED_SETTINGS = (PRIMARY, (100., 10.), (108., 10.), (104., 8.), (104., 12.))
WINDOWS = ("full", "overlap", "overlap_matched_count")
Z_GRID = np.linspace(*Z, 4097)
CHI_GRID = COSMOLOGY.comoving_distance(Z_GRID).value


def positions(rows):
    ra, dec = np.deg2rad(rows[:, :2]).T
    chi = np.interp(rows[:, 2], Z_GRID, CHI_GRID)
    xyz = chi[:, None]*np.column_stack((np.cos(dec)*np.cos(ra), np.cos(dec)*np.sin(ra), np.sin(dec)))
    return xyz, rows[:, 3]*rows[:, 4]


def count(tree_a, tree_b, w_a, w_b):
    # The zero-distance self terms of an autocorrelation are below the first edge.
    t = tree_a.count_neighbors(tree_b, EDGES, weights=(w_a, w_b), cumulative=False)
    return t[1:]


def landy_szalay(galaxies, randoms):
    d, wd = positions(galaxies)
    r, wr = positions(randoms)
    dt, rt = cKDTree(d), cKDTree(r)
    sd, sr = wd.sum(), wr.sum()
    norms = np.array([sd**2-wd@wd, sd*sr, sr**2-wr@wr])
    if np.any(norms <= 0):
        raise ValueError("Too few positively weighted points for pair normalisation")
    sums = np.stack((count(dt, dt, wd, wd), count(dt, rt, wd, wr), count(rt, rt, wr, wr)))
    dd, dr, rr = sums/norms[:, None]
    if np.any(rr <= 0):
        raise ValueError("Random counts must populate each separation bin")
    xi = (dd-2*dr+rr)/rr
    return {"data_count": len(d), "random_count": len(r), "pair_sums_dd_dr_rr": sums.tolist(),
            "pair_normalisations_dd_dr_rr": norms.tolist(), "xi": xi.tolist()}


def per_mock(mock, cache):
    result = {"mock": mock, "windows": {}, "inputs": []}
    samples = {window: {"galaxy": [], "random": []} for window in WINDOWS[:2]}
    for cap in CAPS:
        for kind in ("galaxy", "random"):
            with np.load(cache/f"mock{mock}-{cap}-{kind}.npz", allow_pickle=False) as f:
                result["inputs"].append(json.loads(str(f["metadata"])))
                for window in samples:
                    samples[window][kind].append(f[window])
    sample = {w: {k: np.concatenate(v) for k, v in s.items()} for w, s in samples.items()}
    previous = json.loads((HERE/"results"/"window_measurements.json").read_text())
    target_count = next(b["galaxies"]["inside"]["mer_wide"]["n"] for b in previous["bins"] if b["z"] == list(Z))
    overlap = sample["overlap"]
    rng = np.random.default_rng([SEED, mock, 11])
    pick = np.sort(rng.choice(len(overlap["galaxy"]), target_count, replace=False))
    sample["overlap_matched_count"] = {"galaxy": overlap["galaxy"][pick], "random": overlap["random"]}
    for window, value in sample.items():
        result["windows"][window] = landy_szalay(value["galaxy"], value["random"])
        print(f"mock {mock:02d} {window}: computed \u03be", flush=True)
    return result


def regressions():
    # Standard smooth inverse-distance terms absorb the local broadband level,
    # slope, and curvature. The fit uses the same bin weights in both windows.
    broad = (104./CENTRES[:, None])**np.arange(3)
    projector = np.eye(len(CENTRES))-broad@np.linalg.pinv(broad)
    template = lambda peak, width: np.exp(-.5*((CENTRES-peak)/width)**2)
    fixed = np.stack([projector@template(*setting) for setting in FIXED_SETTINGS])
    scan = np.stack([projector@template(peak, PRIMARY[1]) for peak in PEAK_GRID])
    return projector, fixed, scan


def fit_xi(values):
    p, fixed, scanned = regressions()
    residual = values@p
    amplitude = (residual@fixed.T)/np.sum(fixed*fixed, axis=1)
    dot = np.maximum(0, residual@scanned.T)
    improvements = dot**2/np.sum(scanned*scanned, axis=1)
    best = improvements.argmax(axis=-1)
    peaks = np.where(improvements.max(axis=-1)>0, PEAK_GRID[best], np.nan)
    return amplitude, peaks


def injection_recovery(xi, full_amplitude):
    """Inject known centres into each mock minus the mean of the other mocks."""
    n = xi.shape[1]
    held_out_noise = (n*xi-xi.sum(axis=1, keepdims=True))/(n-1)
    injected_amplitude = (full_amplitude.sum()-full_amplitude)/(n-1)
    if np.any(injected_amplitude <= 0):
        return {"status": "Full-window training amplitudes are not consistently positive"}
    trials = []
    for centre in (96., 104., 112.):
        template = np.exp(-.5*((CENTRES-centre)/PRIMARY[1])**2)
        _, recovered = fit_xi(held_out_noise+injected_amplitude[None, :, None]*template)
        within = np.abs(recovered-centre) <= 8.
        trials.append({"injected_centre": centre,
                       "mock_peaks_by_window": [[float(p) if np.isfinite(p) else None for p in row]
                                                for row in recovered],
                       "within_8_h_inv_mpc_by_window": within.sum(axis=1).tolist()})
    return {"template_amplitude_by_held_out_mock": injected_amplitude.tolist(),
            "success_tolerance_h_inv_mpc": 8., "trials": trials}


def describe(results):
    xi = np.stack([np.stack([mock["windows"][window]["xi"] for mock in results]) for window in WINDOWS])
    if len(results) < 2:
        raise ValueError("At least two paired mock realisations are necessary")
    amplitude, peaks = fit_xi(xi)
    _, mean_peaks = fit_xi(xi.mean(axis=1))
    rng = np.random.default_rng(SEED+1)
    resamples = rng.integers(len(results), size=(10_000, len(results)))
    shifted = amplitude[1:]-amplitude[0]
    pairs = np.concatenate((amplitude, shifted), axis=0)
    bootstrap = np.quantile(pairs[:, resamples, :].mean(axis=2), [.025, .975], axis=1)
    summary = {"fixed_template_settings_h_inv_mpc": FIXED_SETTINGS,
               "primary_amplitude_by_window_then_mock": amplitude[:, :, 0].tolist(),
               "fixed_template_means": pairs.mean(axis=1).tolist(),
               "fixed_template_bootstrap_95_pct": bootstrap.tolist(),
               "primary_amplitude_sample_sd": amplitude[:, :, 0].std(axis=1, ddof=1).tolist(),
               "fixed_template_summary_rows": [*WINDOWS, "overlap_minus_full", "overlap_matched_count_minus_full"],
               "mean_xi": xi.mean(axis=1).tolist(),
               "xi_mock_sample_sd": xi.std(axis=1, ddof=1).tolist(),
               "injected_centre_check": injection_recovery(xi, amplitude[0, :, 0])}
    summary["free_peak_by_window_then_mock_h_inv_mpc"] = [[float(x) if np.isfinite(x) else None
                                                         for x in row] for row in peaks]
    summary["free_peak_of_mean_h_inv_mpc"] = [float(v) if np.isfinite(v) else None for v in mean_peaks]
    return summary


def write_results(results, cache, output):
    with (cache/MASK_FILES["mer_wide"]).open("rb") as f:
        mask_sha256 = hashlib.file_digest(f, "sha256").hexdigest()
    prior = json.loads((HERE/"input_files.json").read_text())
    if mask_sha256 != prior[MASK_FILES["mer_wide"]]["sha256"]:
        raise ValueError("The Euclid mask differs from the one used in the pair-retention calculation")
    doc = {"redshift": Z, "s_edges_h_inv_mpc": EDGES.tolist(), "s_centres_h_inv_mpc": CENTRES.tolist(),
           "full_thinning_probabilities": FULL_KEEP, "thinning_seed": SEED,
           "mer_wide_moc_sha256": mask_sha256, "windows": WINDOWS,
           "peak_scan_limits_h_inv_mpc": [float(PEAK_GRID[0]), float(PEAK_GRID[-1])],
           "results": results, "summary": describe(results)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--mocks", type=int, nargs="+", default=MOCKS)
    parser.add_argument("--output", type=Path, default=HERE/"results"/"mock_recovery.json")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if len(set(args.mocks)) != len(args.mocks):
        parser.error("Mock IDs must be unique")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda i: per_mock(i, args.cache), args.mocks))
    write_results(results, args.cache, args.output)
