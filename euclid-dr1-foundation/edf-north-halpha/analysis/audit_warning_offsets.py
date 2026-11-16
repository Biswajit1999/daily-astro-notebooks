"""Measure coverage and signed fit scores around off-line centres in both grisms."""
import argparse
import json
from pathlib import Path
import sys

import pandas as pd

HERE = Path(__file__).resolve().parent
EUCLID = HERE.parents[1]
DAY3 = EUCLID / "day03-cross-grism" / "analysis"
sys.path.insert(0, str(DAY3))
from compare_grisms import DAY2, GRISMS, OFFSETS, fits, get_hats_spectrum, read_subset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", default=HERE, type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    parent = pd.read_csv(DAY2 / "observed_results" / "all_morphology_matched.csv.gz")
    spectra, inputs = read_subset(args.cache, parent)
    original = pd.read_csv(DAY3 / "overlap_fits.csv.gz")
    fits_by_offset = []
    for object_id, block in original.groupby("object_id"):
        tile = block.tileid.iloc[0]
        observed = dict(zip(GRISMS, (get_hats_spectrum(spectra, object_id, tile, g) for g in GRISMS), strict=True))
        if any(count != 1 for _, count in observed.values()):
            raise ValueError(f"Unexpected spectrum multiplicity for {object_id}")
        for row in block.itertuples(index=False):
            record = {"object_id": object_id, "tileid": tile, "offset_A": row.offset_A}
            for grism, (spectrum, _) in observed.items():
                fit = fits(spectrum, row.centre_A, allow_warning=True)
                record.update({f"{grism}_{key}": value for key, value in fit.items()})
            fits_by_offset.append(record)

    table = pd.DataFrame(fits_by_offset)
    dual = table.BGS_status.eq("fitted") & table.RGS_status.eq("fitted")
    above = table.BGS_snr.ge(5) & table.RGS_snr.ge(5)
    below = table.BGS_snr.le(-5) & table.RGS_snr.le(-5)
    table = table.assign(dual_fit=dual, dual_above_5=above, dual_below_minus_5=below)
    line_ids = set(table.loc[table.offset_A.eq(0) & dual, "object_id"])
    common = table.loc[dual].groupby("object_id").size().eq(len(OFFSETS))
    counts = []
    for offset, group in table.groupby("offset_A"):
        counts.append({
            "offset_A": int(offset),
            "nominal_windows": len(group),
            "dual_fits": int(group.dual_fit.sum()),
            "dual_above_5": int(group.dual_above_5.sum()),
            "dual_below_minus_5": int(group.dual_below_minus_5.sum()),
            "dual_fits_in_line_eligible_objects": int((group.dual_fit & group.object_id.isin(line_ids)).sum()),
        })
    report = {"offsets": counts, "common_dual_fits_all_centres": int(common.sum()), "inputs": inputs}
    table.to_csv(args.output / "warning_offset_fits.csv.gz", index=False, float_format="%.9g",
                 compression={"method": "gzip", "mtime": 0})
    (args.output / "warning_offset_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
