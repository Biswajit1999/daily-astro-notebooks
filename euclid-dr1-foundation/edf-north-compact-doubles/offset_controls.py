"""Repeat the NISP-J positional test along eight sky directions."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
from pathlib import Path

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
import numpy as np

from archive import image_strip
from search_doubles import dog, j_check


ANGLES = tuple(range(0, 360, 45))
TESTABLE = {"pass", "no_repeat", "no_local_peak"}


def tile_controls(tile, rows, cache):
    data, header, meta = image_strip(tile, "J", cache)
    origin = meta["origin_xy"]
    wcs = WCS(header).celestial
    jmap, valid = dog(data, 1.25, 3.5)
    positions = SkyCoord(
        [[float(row["ra1"]), float(row["ra2"])] for row in rows],
        [[float(row["dec1"]), float(row["dec2"])] for row in rows],
        unit="deg",
    )
    results = []
    for angle in ANGLES:
        shifted = positions.directional_offset_by(angle * u.deg, 3 * u.arcsec)
        x, y = wcs.world_to_pixel(shifted)
        states = [j_check(jmap, valid, (xx, yy))["state"]
                  for xx, yy in zip(x - origin[0], y - origin[1], strict=True)]
        for row, state in zip(rows, states, strict=True):
            if angle == 0 and row["shift_state"] != state:
                raise ValueError(f"North-shift replay disagrees for {row['id']}")
            results.append({
                "tile": tile,
                "candidate_id": row["id"],
                "angle_deg": angle,
                "state": state,
                "on_target_state": row["j_state"],
            })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    with args.candidates.open(newline="") as f:
        rows = list(csv.DictReader(f))
    groups = {}
    for row in rows:
        groups.setdefault(int(row["tile"]), []).append(row)
    records = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(tile_controls, tile, group, args.cache)
                for tile, group in sorted(groups.items())]
        for job in jobs:
            records.extend(job.result())
    by_angle = {}
    for angle in ANGLES:
        testable = [row for row in records if row["angle_deg"] == angle
                    and row["state"] in TESTABLE]
        paired = [row for row in testable if row["on_target_state"] in TESTABLE]
        by_angle[angle] = {
            "testable": len(testable),
            "shifted_repeats": sum(row["state"] == "pass" for row in testable),
            "paired_testable": len(paired),
            "paired_shifted_repeats": sum(row["state"] == "pass" for row in paired),
            "paired_on_target_repeats": sum(row["on_target_state"] == "pass" for row in paired),
        }
    args.output.mkdir(parents=True, exist_ok=True)
    from search_doubles import write_csv
    write_csv(args.output / "offset_controls.csv.gz", records)
    (args.output / "offset_controls.json").write_text(json.dumps(by_angle, indent=2) + "\n")
    print(json.dumps(by_angle), flush=True)


if __name__ == "__main__":
    main()
