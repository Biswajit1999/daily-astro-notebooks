"""Check VIS size effects after dropping each tile and changing the Hα flux."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_vis_apertures import DAY02, conditional_effect
from audit_spe_line_quality import best_per_source, read_lines, valid_flux_rows
from analyse_day01 import make_strata, pooled_effect


def leave_tile_out(sample):
    frame = sample.sort_values("object_id").assign(
        log_aperture_radius_pix=lambda d: np.log10(d.r50_1p5arcsec),
        log_halpha_flux=lambda d: np.log10(d.ha_flux),
        log_vis_aper_flux_uJy=lambda d: np.log10(d.flux_vis_2fwhm_aper),
    )
    estimates = {}
    for tile in sorted(frame.tileid.unique()):
        subset = frame[frame.tileid != tile]
        cells = make_strata(subset)
        n_cells = sum(len(block) for _, block, _ in cells)
        estimates[str(tile)] = {
            "n": n_cells, "cells": len(cells),
            "effect_dex": pooled_effect(cells) if len(cells) >= 4 and n_cells >= 200 else None,
        }
    return estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line-cache", type=Path, required=True)
    args = parser.parse_args()
    out = DAY02 / "joint_audit"
    visits = pd.read_csv(out / "vis_growth_curves.csv.gz")
    matched = pd.read_csv(DAY02 / "observed_results" / "strict_clean.csv")
    frame = matched.merge(visits, on=["object_id", "tileid"], validate="one_to_one")
    if len(frame) != len(matched):
        raise ValueError("Unmatched VIS clean sources")
    good = valid_flux_rows(read_lines(args.line_cache))
    red, count = best_per_source(good[good.object_id.isin(frame.object_id)], (212,))
    red = red[["object_id", "spe_line_flux_gf"]].rename(columns={"spe_line_flux_gf": "red_flux"})
    selections = {}
    for cut in (2.0, 2.5):
        sample = frame[
            frame.image_status.eq("measured")
            & frame.nominal_aperture_snr_1p5arcsec.ge(15)
            & frame.neighbour_arcsec.ge(cut)
            & frame[["r50_1arcsec", "r50_1p5arcsec", "r50_2arcsec"]].gt(0).all(axis=1)
        ]
        matched_red = sample.merge(red, on="object_id", validate="one_to_one")
        selections[str(cut)] = {
            "n": len(sample),
            "leave_tile_out": leave_tile_out(sample),
            "red_grism": conditional_effect(matched_red.assign(ha_flux=matched_red.red_flux), "r50_1p5arcsec"),
            "day02_median_on_same_objects": conditional_effect(matched_red, "r50_1p5arcsec"),
        }
    result = {"ambiguous_red_fits": count, "minimum_neighbour_distance_arcsec": selections}
    (out / "vis_tile_sensitivity.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
