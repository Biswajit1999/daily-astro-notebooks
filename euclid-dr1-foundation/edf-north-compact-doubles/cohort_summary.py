"""Measure coverage, separation dependence, and tile sensitivity of each run."""
import argparse
import csv
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

from search_doubles import EDGE, WIDTH, wilson


BINS = (0.38, 0.50, 0.62, 0.74, 0.86, 0.951)
SCORE_BINS = (6, 10, 20, np.inf)
TESTABLE = {"pass", "no_repeat", "no_local_peak"}
NOMINAL_PIXEL_AREA = (0.1 / 3600) ** 2


def count_bins(rows):
    return [
        {
            "lo": lo,
            "hi": hi,
            "tested": sum(lo <= row[0] < hi for row in rows),
            "repeat": sum(lo <= row[0] < hi and row[2] for row in rows),
        }
        for lo, hi in zip(BINS[:-1], BINS[1:], strict=True)
    ]


def positive_difference(by_tile):
    """Bootstrap complete tiles with simple pooled bin denominators."""
    counts = np.array([[[r["repeat"], r["tested"]] for r in bins]
                       for bins in by_tile.values()])
    if len(counts) < 2:
        return None
    rng = np.random.default_rng(20261118)
    draws = rng.integers(0, len(counts), (5000, len(counts)))
    totals = counts[draws].sum(axis=1)
    valid = (totals[:, 0, 1] > 0) & (totals[:, -1, 1] > 0)
    totals = totals[valid]
    if not len(totals):
        return None
    differences = totals[:, -1, 0] / totals[:, -1, 1] - totals[:, 0, 0] / totals[:, 0, 1]
    return np.percentile(differences, [2.5, 97.5]).tolist()


def tile_edge(tile, cache, band):
    stem = cache / f"{tile}-{band}"
    header = fits.Header.fromstring(stem.with_suffix(".hdr").read_text(), sep="\n")
    meta = json.loads(stem.with_suffix(".json").read_text())
    x0, y0 = meta["origin_xy"]
    left, right = EDGE - 0.5, WIDTH - EDGE - 0.5
    return WCS(header).celestial.pixel_to_world(
        np.array([left, right, right, left]) + x0,
        np.array([left, left, right, right]) + y0,
    )


def coverage(tiles, cache):
    entries = []
    for entry in tiles:
        if "vis" not in entry or "j" not in entry:
            continue
        tile = entry["tile"]
        products = [entry["vis"], entry["j"]]
        data = {}
        for band in ("VIS", "J"):
            filename = cache / f"{tile}-{band}.npy"
            image = np.load(filename, mmap_mode="r")[EDGE:-EDGE, EDGE:-EDGE]
            data[band] = np.isfinite(image) & (image != 0)
        vis, j = (tile_edge(tile, cache, band) for band in ("VIS", "J"))
        if np.max(vis.separation(j).arcsec) > 0.001:
            raise ValueError(f"Pixel coverage needs a reprojection in tile {tile}")
        entries.append({
            "tile": tile,
            "corners_deg": np.column_stack((vis.ra.deg, vis.dec.deg)).tolist(),
            "valid_vis_pixels": int(data["VIS"].sum()),
            "valid_j_pixels": int(data["J"].sum()),
            "valid_common_pixels": int(np.count_nonzero(data["VIS"] & data["J"])),
            "image_payload_bytes": sum(
                r["end_exclusive"] - r["start"] for p in products for r in p["ranges"]
            ),
        })
    return entries


def intersect_corners(first, second):
    anchor = SkyCoord(*np.mean(first, axis=0), unit="deg")
    polys = []
    for corners in (first, second):
        sky = SkyCoord(np.array(corners)[:, 0], np.array(corners)[:, 1], unit="deg")
        east, north = anchor.spherical_offsets_to(sky)
        polys.append(np.column_stack((east.deg, north.deg)))
    for poly in polys:
        dx, dy = np.diff(np.vstack((poly, poly[0])), axis=0).T
        for axis in np.column_stack((-dy, dx)):
            a, b = (p @ axis for p in polys)
            if max(a.min(), b.min()) >= min(a.max(), b.max()):
                return False
    return True


def read_cohort(root, cache):
    through = json.loads((root / "search_summary.json").read_text())
    with (root / "candidates.csv").open(newline="") as f:
        candidates = list(csv.DictReader(f))
    by_tile_rows = {}
    scored = {}
    for row in candidates:
        if row["j_state"] not in TESTABLE:
            continue
        tile = int(row["tile"])
        item = (float(row["sep_arcsec"]),
                min(float(row["vis_score1"]), float(row["vis_score2"])),
                row["j_state"] == "pass")
        by_tile_rows.setdefault(tile, []).append(item)
        for index, (lo, hi) in enumerate(zip(SCORE_BINS[:-1], SCORE_BINS[1:], strict=True)):
            if lo <= item[1] < hi:
                scored.setdefault(index, []).append(item)
    by_tile = {tile: count_bins(rows) for tile, rows in by_tile_rows.items()}
    counts = count_bins([row for rows in by_tile_rows.values() for row in rows])
    for item in counts:
        item["wilson95"] = wilson(item["repeat"], item["tested"])
    good = coverage(through["tiles"], cache)
    numbers = {k: v for k, v in through.items() if k != "tiles"}
    numbers.update(bins=counts, tile_bootstrap95_wide_minus_narrow=positive_difference(by_tile),
                   bins_by_tile=by_tile,
                   bins_by_weaker_vis_score={i: count_bins(rows) for i, rows in scored.items()},
                   coverage=good,
                   missing=[{"tile": t["tile"], **{k: v for k, v in t.items() if k.endswith("_error")}}
                            for t in through["tiles"] if "vis" not in t or "j" not in t])
    return numbers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--pilot-cache", type=Path, required=True)
    parser.add_argument("--holdout", type=Path)
    parser.add_argument("--holdout-cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"pilot": read_cohort(args.pilot, args.pilot_cache)}
    if args.holdout:
        result["holdout"] = read_cohort(args.holdout, args.holdout_cache)
    images = [entry for cohort in result.values() for entry in cohort["coverage"]]
    overlaps = []
    for i, first in enumerate(images):
        for second in images[:i]:
            if intersect_corners(first["corners_deg"], second["corners_deg"]):
                overlaps.append([first["tile"], second["tile"]])
    area = sum(row["valid_common_pixels"] for row in images) * NOMINAL_PIXEL_AREA
    result["total"] = {
        "paired_tiles": len(images),
        "overlapping_tile_pairs": overlaps,
        "nonoverlapping_common_area_deg2": area if not overlaps else None,
        "common_area_sum_deg2": area,
        "two_band_pixel_payload_bytes": len(images) * WIDTH * WIDTH * 2 * 4,
        "fits_image_range_bytes": sum(row["image_payload_bytes"] for row in images),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["total"], indent=2))


if __name__ == "__main__":
    main()
