"""Recheck the archived EDF North pilot. Optionally verify the original MER FITS."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyse_day01 import make_strata, pooled_effect


RESULTS = Path(__file__).resolve().parents[1] / "real_results"
TILE = 101834044
IMAGE_FIELDS = ["kron_radius", "flag_vis", "det_quality_flag", "spurious_prob"]
FITS_FIELDS = IMAGE_FIELDS + ["flux_vis_2fwhm_aper"]
N_BOOT = 10000
SEED = 20261119


def read_table(path):
    table = pd.read_csv(path, dtype={"object_id": "string"}, float_precision="round_trip")
    if not table["object_id"].str.fullmatch(r"\d+").fillna(False).all():
        raise ValueError(f"Missing or malformed object ID in {path}")
    table = table.set_index("object_id")
    if not table.index.is_unique:
        raise ValueError(f"Duplicate object ID in {path}")
    return table


def imaging_pass(table):
    return table.flag_vis.eq(0) & table.det_quality_flag.eq(0) & table.spurious_prob.lt(0.5)


def check_same_rows(actual, archived):
    pd.testing.assert_frame_equal(
        actual.sort_index(), archived.sort_index(), check_dtype=False, rtol=1e-12, atol=0,
    )


def validated_tables(results=RESULTS):
    selected = read_table(results / "selected_426.csv")
    matched = read_table(results / "size_matched_327.csv")
    archived_pass = read_table(results / "strict_quality_150.csv")
    selected_ok = (
        selected.spe_z.between(0.9, 1.5) & selected.spe_z_prob.between(0.99, 1)
        & selected.vis_det.eq(1) & np.isfinite(selected.flux_vis_2fwhm_aper)
        & selected.flux_vis_2fwhm_aper.gt(0)
        & np.isfinite(selected.ha_flux) & selected.ha_flux.gt(0)
        & np.isfinite(selected.ha_snr) & selected.ha_snr.ge(5)
        & selected.n_line_entries.ge(1)
    )
    if not selected_ok.all():
        raise ValueError("Archived selected rows fail the documented object-level cuts.")
    if not (matched.tileid.eq(TILE) & matched.kron_radius.gt(0) & np.isfinite(matched.kron_radius)).all():
        raise ValueError("A morphology match has the wrong tile or an invalid aperture.")
    check_same_rows(matched[selected.columns], selected.loc[matched.index])
    passing = matched.loc[imaging_pass(matched)]
    check_same_rows(passing, archived_pass)
    return selected, matched, passing


def verify_mer(path, selected, matched):
    from astropy.io import fits

    with fits.open(path, memmap=True) as hdus:
        catalogue = hdus["EUC_MER__FINAL_CATALOG"]
        if catalogue.columns["KRON_RADIUS"].unit != "pix":
            raise ValueError("Unexpected Kron radius unit in the MER catalogue.")
        ids = pd.Index(np.asarray(catalogue.data["OBJECT_ID"]).astype(str), dtype="string", name="object_id")
        values = {name: np.asarray(catalogue.data[name.upper()]).astype(float) for name in FITS_FIELDS}
    raw = pd.DataFrame(values, index=ids)
    if not raw.index.is_unique:
        raise ValueError("Non-unique MER FITS identifiers.")
    raw_matches = raw.loc[raw.index.intersection(selected.index)]
    raw_matches = raw_matches.loc[np.isfinite(raw_matches.kron_radius) & raw_matches.kron_radius.gt(0)]
    check_same_rows(raw_matches, matched[FITS_FIELDS])
    with Path(path).open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"catalogue_rows": len(raw), "verified_matches": len(raw_matches), "sha256": sha256}


def radius_summary(table, rng):
    radius = table.kron_radius.to_numpy()
    boot = np.median(rng.choice(radius, size=(N_BOOT, len(radius)), replace=True), axis=1)
    return {"n": len(table), "median_px": float(np.median(radius)),
            "object_bootstrap_95_px": np.quantile(boot, [0.025, 0.975]).tolist()}


def strata_summary(table, *, report_exploratory_contrast=False):
    values = table.assign(log_vis_aper_flux_uJy=np.log10(table.flux_vis_2fwhm_aper),
                          log_halpha_flux=np.log10(table.ha_flux),
                          log_aperture_radius_pix=np.log10(table.kron_radius))
    cells = make_strata(values)
    result = {"eligible_cells": len(cells), "eligible_objects": sum(len(rows) for _, rows, _ in cells)}
    if report_exploratory_contrast and cells:
        result["exploratory_contrast_dex"] = pooled_effect(cells)
    return result


def audit(selected, matched, passing):
    excluded = matched.drop(index=passing.index)
    rng = np.random.default_rng(SEED)
    radii = {"retained": radius_summary(passing, rng), "excluded": radius_summary(excluded, rng)}
    return {
        "counts": {"selected": len(selected), "morphology_matched": len(matched),
                   "imaging_quality_pass": len(passing), "not_matched": len(selected) - len(matched)},
        "selected_by_tile": {str(tile): count for tile, count in selected.tileid.value_counts().items()},
        "flags": {"nonzero_VIS": int(matched.flag_vis.ne(0).sum()),
                  "nonzero_detection_quality": int(matched.det_quality_flag.ne(0).sum()),
                  "spurious_probability_ge_0_5": int(matched.spurious_prob.ge(0.5).sum())},
        "kron_radius": radii,
        "median_pct_change_retained_vs_excluded": 100 * (
            radii["retained"]["median_px"] / radii["excluded"]["median_px"] - 1
        ),
        "comparison": {"before_imaging_cuts": strata_summary(matched, report_exploratory_contrast=True),
                       "after_imaging_cuts": strata_summary(passing),
                       "design_minimum_objects": 200, "design_minimum_cells": 4},
        "bootstrap": {"draws": N_BOOT, "seed": SEED, "unit": "object within observed flag group",
                      "scope": "Descriptive within-tile intervals. Spatial dependence and catalogue systematics are outside this resampling."},
    }


def plot_audit(result, target):
    fig, (flow, sizes) = plt.subplots(1, 2, figsize=(10.8, 4.1), layout="constrained")
    counts = result["counts"]
    bars = flow.barh(["Line-selected", "MER morphology matched", "Passed imaging cuts"],
                     [counts["selected"], counts["morphology_matched"], counts["imaging_quality_pass"]],
                     color=["0.25", "0.43", "0.62"], height=0.59)
    flow.bar_label(bars, padding=5, fontsize=11)
    flow.invert_yaxis()
    flow.set(xlim=(0, 490), xlabel="Unique catalogue objects", title="A   Sample retained by each step", xticks=[0,100,200,300,400])
    for y, (label, row) in enumerate(result["kron_radius"].items()):
        low, high = row["object_bootstrap_95_px"]
        median = row["median_px"]
        sizes.errorbar(median, y, xerr=[[median-low],[high-median]], color="0.20",
                       fmt="o" if y==0 else "s", capsize=4, markersize=7)
        sizes.text(0.98, y+0.19, f"{median:.2f} px", ha="right", va="top",
                   transform=sizes.get_yaxis_transform(), fontsize=10)
    sizes.set(yticks=[0,1], yticklabels=[f"Retained (n={result['kron_radius']['retained']['n']})",
                                        f"Excluded (n={result['kron_radius']['excluded']['n']})"],
              ylim=(1.53,-0.53), xlabel="Median MER Kron radius (pixels)",
              title="B   Catalogue apertures in the matched tile")
    for ax in (flow, sizes):
        ax.spines[["top","right","left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color="0.91")
        ax.set_axisbelow(True)
    fig.savefig(target, dpi=210, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mer-fits", type=Path, help="Original IRSA MER final catalogue for tile 101834044.")
    args = parser.parse_args()
    selected, matched, passing = validated_tables()
    result = audit(selected, matched, passing)
    if args.mer_fits:
        result["original_mer_fits"] = verify_mer(args.mer_fits, selected, matched)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "day01_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    plot_audit(result, args.output / "day01_sample_audit.png")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
