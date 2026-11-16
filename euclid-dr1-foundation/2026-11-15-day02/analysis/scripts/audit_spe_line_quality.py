"""Measure the effect of documented SPE Gaussian-fit flags on the Day 02 pilot."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

DAY02 = Path(__file__).resolve().parents[1]
DAY01_SCRIPTS = DAY02.parents[1] / "2026-11-14-day01" / "analysis" / "scripts"
sys.path.insert(0, str(DAY01_SCRIPTS))
from analyse_day01 import test_effect

HATS = (
    "s3://nasa-irsa-euclid-dr1/contributed/dr1/hats/reformatted_catalogs/"
    "spectro_line_features_spe_line_features_deep/"
)
COLUMNS = [
    "object_id", "spe_rank", "spe_line_name", "spe_line_qual_gf", "spe_line_snr_gf",
    "spe_line_flux_gf", "spe_line_flux_err_gf", "spe_line_central_wl_gf",
]
GOOD = (211, 212, 213)
# Prefer the pipeline's good combined measurement. Then use good red, then blue.
GRISM_PRIORITY = {213: 0, 212: 1, 211: 2}


def read_lines(cache):
    import dask
    import lsdb

    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        catalog = lsdb.open_catalog(
            HATS, storage_options={"anon": True},
            search_filter=lsdb.ConeSearch(269.733, 66.018, 0.28 * 3600),
            columns=COLUMNS, filters=[("spe_rank", "==", 0), ("spe_line_name", "==", "Halpha")],
        )
        with dask.config.set(num_workers=1):
            lines = catalog.query("spe_rank == 0 and spe_line_name == 'Halpha'").compute()
        tmp = cache.with_suffix(".part")
        lines.reset_index(drop=True).to_parquet(tmp)
        tmp.replace(cache)
    return pd.read_parquet(cache).loc[:, COLUMNS]


def valid_flux_rows(lines):
    flux, error, snr = (lines[col].to_numpy(dtype=float) for col in ("spe_line_flux_gf", "spe_line_flux_err_gf", "spe_line_snr_gf"))
    return lines.loc[
        np.isfinite(flux) & np.isfinite(error) & np.isfinite(snr)
        & (flux > 0) & (error > 0) & (snr >= 5)
    ].copy()


def best_per_source(lines, codes):
    eligible = lines[lines.spe_line_qual_gf.isin(codes)].copy()
    eligible["priority"] = eligible.spe_line_qual_gf.map(GRISM_PRIORITY)
    best = eligible[eligible.priority == eligible.groupby("object_id").priority.transform("min")]
    ambiguous = best.object_id.duplicated(keep=False)
    return best.loc[~ambiguous], int(best.loc[ambiguous, "object_id"].nunique())


def compare(matched, flux):
    frame = matched.merge(flux, on="object_id", validate="one_to_one")
    frame["log_halpha_flux"] = np.log10(frame.audit_flux)
    frame["log_vis_aper_flux_uJy"] = np.log10(frame.flux_vis_2fwhm_aper)
    frame["log_aperture_radius_pix"] = np.log10(frame.kron_radius)
    frame = frame.sort_values("object_id")
    # Keep the Day 02 seed while using the Day 01 resampling implementation.
    return {"n_objects": len(frame), **test_effect(frame, seed=20261115)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DAY02 / "spectral_audit")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lines = read_lines(args.cache)
    clean_path = DAY02 / "observed_results" / "strict_clean.csv"
    clean = pd.read_csv(clean_path)
    lines = lines[lines.object_id.isin(clean.object_id)]
    valid = valid_flux_rows(lines)
    published_flux = clean[["object_id", "ha_flux"]].rename(columns={"ha_flux": "audit_flux"})
    rebuilt = valid.groupby("object_id", as_index=False).spe_line_flux_gf.median()
    rebuilt = published_flux.merge(rebuilt, on="object_id", validate="one_to_one")
    if len(rebuilt) != len(clean):
        raise ValueError("Live line data did not recover the full published Day 02 clean cohort")
    np.testing.assert_allclose(rebuilt.audit_flux, rebuilt.spe_line_flux_gf, rtol=1e-7)

    flag_counts = (
        valid.groupby("spe_line_qual_gf", dropna=False)
        .agg(rows=("object_id", "size"), objects=("object_id", "nunique")).reset_index()
    )
    flag_counts.to_csv(args.output / "spe_quality_counts.csv", index=False)
    spectral_audit = DAY02 / "observed_results" / "matched_spectra" / "matched_spectrum_audit.json"
    matched_ids = [
        row["object_id"] for tile in json.loads(spectral_audit.read_text())["examined_tiles"]
        for row in tile["matches"]
    ]
    (
        lines[lines.object_id.isin(matched_ids)]
        .sort_values(["object_id", "spe_line_qual_gf"])
        .to_csv(args.output / "spe_flags_for_spectral_matches.csv", index=False)
    )
    comparisons = {"day02_median": compare(clean, published_flux)}
    for label, codes in (("good_prefer_combined", GOOD), ("good_red_only", (212,))):
        best, ambiguous = best_per_source(valid, codes)
        flux = best[["object_id", "spe_line_flux_gf"]].rename(columns={"spe_line_flux_gf": "audit_flux"})
        published_on_subset = published_flux[published_flux.object_id.isin(best.object_id)]
        comparisons[label] = {
            "excluded_same_priority_duplicates": ambiguous,
            "selected_codes": {str(int(k)): int(n) for k, n in best.spe_line_qual_gf.value_counts().items()},
            "selected_good_flux": compare(clean, flux),
            "day02_median_flux_on_same_objects": compare(clean, published_on_subset),
        }
    summary = {
        "hats_url": HATS, "cone_deg": [269.733, 66.018, 0.28],
        "clean_catalogue_sha256": hashlib.sha256(clean_path.read_bytes()).hexdigest(),
        "rank0_halpha_rows_for_clean_objects": len(lines),
        "positive_flux_error_and_snr_ge5_rows": len(valid),
        "valid_rows_outside_good_gf_codes": int((~valid.spe_line_qual_gf.isin(GOOD)).sum()),
        "objects_with_valid_rows_outside_good_gf_codes": int(
            valid.loc[~valid.spe_line_qual_gf.isin(GOOD), "object_id"].nunique()
        ),
        "day02_median_recovered_for_all_objects": True,
        "package_versions": {pkg: version(pkg) for pkg in ("lsdb", "numpy", "pandas")},
        "comparisons": comparisons,
    }
    (args.output / "spe_quality_effects.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
