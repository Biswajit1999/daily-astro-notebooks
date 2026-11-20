"""Extend the ACT--SPT-GMOS cross-match to the rest of the archive shortlist."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from astropy.table import Table
from mocpy import MOC
import numpy as np

from measure_spectroscopy import (
    HEALPIX, HERE, angular_grid, distance_match, download, mask_at, measure, read_tables, samples,
)

PILOT = HERE / "results/spectroscopy_results.json"
MANIFEST = HERE / "extension_inputs.json"
RESULT = HERE / "results/extended_sample.json"
SELECTIONS = ("optical", "common_footprint", "j_detection",
              "optical_allow_extended_area", "common_allow_extended_area")


def sample_summary(fields):
    valid = [f for f in fields if "tallies" in f]
    counts = {
        key: {
            metric: sum(f["tallies"][key][metric] for f in valid)
            for metric in ("count", "red")
        }
        for key in SELECTIONS
    }
    return {
        "fields_with_results": len(valid),
        "fields_with_strict_optical_galaxies": sum(f["tallies"]["optical"]["count"] > 0 for f in valid),
        "outskirts_spectra_in_measured_fields": sum(f["outskirts_candidates"] for f in valid),
        "distinct_euclid_galaxies": sum(f["unique_mer_matches"] for f in valid),
        "counts": counts,
        "fields_with_shared_footprint_loss": [
            f["act_name"] for f in valid
            if f["tallies"]["common_footprint"]["count"] < f["tallies"]["optical"]["count"]
        ],
        "fields_with_j_photometry_loss": [
            f["act_name"] for f in valid
            if f["tallies"]["j_detection"]["count"] < f["tallies"]["common_footprint"]["count"]
        ],
    }




def narrower_velocity_check(fields):
    """Recount the same matched galaxies after changing the velocity window."""
    selected = [
        row["match"] for field in fields for row in field["matched_spectra"]
        if row.get("used_in_counts") and abs(row["dv_kms"]) <= 1500
    ]
    return {
        "window_kms": 1500,
        "distinct_euclid_galaxies": len(selected),
        "counts": {
            key: {
                "count": sum(row[key] for row in selected),
                "red": sum(row[key] and row["red_colour"] for row in selected),
            }
            for key in SELECTIONS
        },
    }

def band_coverage(field, paths):
    """Audit actual single-band weights independently of the spectrum matches."""
    a, d, theta = (field[k] for k in ("ra_deg", "dec_deg", "theta500_arcmin"))
    lon, lat = angular_grid(np.radians([a]), np.radians([d]), np.array([theta]), (1, 2), samples(15, 663))
    cells = HEALPIX.lonlat_to_healpix(lon.ravel(), lat.ravel())
    values = {}
    for band in ("VIS", "NIR_Y", "NIR_J", "NIR_H"):
        weight = np.full(len(cells), np.nan)
        for tile, files in paths.items():
            if band in files:
                weight = np.fmax(weight, mask_at(files[band], int(tile), band, cells))
        present = np.isfinite(weight)
        values[band] = {
            "represented_fraction": float(present.mean()),
            "positive_weight_fraction": float((weight > 0).mean()),
            "mean_where_represented": float(weight[present].mean()) if present.any() else None,
        }
    return values

def run(data, manifest_path, result_path):
    inputs = json.loads(manifest_path.read_text())
    prior = json.loads(PILOT.read_text())
    base = json.loads((HERE / "inputs.json").read_text())
    archives = ("act", "spt_gmos", "mer_moc")
    jobs = {
        row["archive"]: (row["url"], data / row["file"])
        for row in base["catalogues"] if row["archive"] in archives
    }
    for t, bands in inputs["tiles"].items():
        for b, url in bands.items():
            jobs[(t, b)] = (url, data / t / url.rsplit("/", 1)[-1])
    with ThreadPoolExecutor(max_workers=7) as pool:
        files = dict(zip(jobs, pool.map(lambda item: download(*item), jobs.values()), strict=True))
    act = Table.read(files["act"][0])
    gm = read_tables(files["spt_gmos"][0])
    moc = MOC.from_fits(files["mer_moc"][0])
    _, candidates, spectra = distance_match(act, gm, moc)
    fields = []
    for field in candidates:
        name = field["act_name"]
        if name not in inputs["fields"]:
            continue
        spec = spectra[name]
        tiles = inputs["fields"][name]["selected"]
        paths = {
            tile: {band: files[(tile, band)][0] for band in inputs["tiles"][tile]}
            for tile in tiles
        }
        bands = band_coverage(field, paths)
        result = measure(field, spec, paths, record_weights=True)
        fields.append(dict(result, band_weights=bands))
        print(name, result["unique_mer_matches"], flush=True)
    if len(fields) != len(inputs["fields"]):
        raise ValueError("Field inventory and catalogue screen disagree")
    result = {
        "summary_all": sample_summary(prior["measured_fields"] + fields),
        "summary_extension": sample_summary(fields),
        "velocity_sensitivity": narrower_velocity_check(prior["measured_fields"] + fields),
        "fields": fields,
        "sha256": {"/".join(key) if isinstance(key, tuple) else key: item[1] for key, item in files.items()},
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / "data")
    parser.add_argument("--inputs", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, default=RESULT)
    args = parser.parse_args()
    run(args.data, args.inputs, args.output)
