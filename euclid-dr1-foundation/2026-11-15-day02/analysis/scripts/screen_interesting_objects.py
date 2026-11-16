"""Screen the pilot for multi-line spectra and repeatable individual Hα detections."""
import argparse
import json
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd

from audit_grism_halpha import DAY02, read_hats, fit_window
from audit_secondary_lines import LINES

# Include a separate line for a cross-check where the red spectrum covers it.
TRANSITIONS = {**LINES, "SII6718": 6718.29}
SNR = "sigma_30A_formal_snr"
RMS = "sigma_30A_sideband_rms"


def read_subset(cache, pilot):
    # read_hats filters the three existing checksum-verified partitions by ID.
    # Its list may include IDs outside these three partitions, so explicitly
    # select only the IDs in their published HEALPix cells before the read.
    from cdshealpix import lonlat_to_healpix
    from audit_grism_halpha import PARTITIONS

    ra = pilot.ra_from_object_id.to_numpy() * u.deg
    dec = pilot.dec_from_object_id.to_numpy() * u.deg
    inside = np.zeros(len(pilot), dtype=bool)
    for order, pixel in PARTITIONS:
        inside |= lonlat_to_healpix(ra, dec, order) == pixel
    selected = pilot.loc[inside, ["object_id", "tileid"]]
    return read_hats(selected.to_dict("records"), cache)


def scan(spectra, pilot):
    sample = spectra.merge(pilot, on=["object_id", "tileid"], validate="many_to_one")
    if len(sample) != len(spectra) or sample.duplicated(["object_id", "lrange"]).any():
        raise ValueError("Unexpected spectra identity or multiplicity")
    rows = []
    for item in sample.itertuples(index=False):
        spectrum = pd.DataFrame(item.spectrum).astype(float)
        for name, rest in TRANSITIONS.items():
            centre = rest * (1 + item.spe_z)
            fit, _ = fit_window(spectrum, centre)
            rms = fit.get(RMS)
            score = fit[SNR] / max(1, rms) if rms is not None else None
            width_scores = {
                f"screen_snr_sigma_{w}A": (
                    fit[f"sigma_{w}A_formal_snr"] / max(1, fit[f"sigma_{w}A_sideband_rms"])
                ) if rms is not None else None for w in (20, 45)
            }
            rows.append({"object_id": int(item.object_id), "tileid": int(item.tileid),
                         "grism": item.lrange, "line": name, "centre_A": centre,
                         "status": fit["status"], "formal_snr": fit.get(SNR),
                         "sideband_rms": rms, "screen_snr": score, **width_scores})
    return pd.DataFrame(rows)


def candidates(pilot, fits_table, namespace):
    dither = pd.read_csv(DAY02 / "validation" / "red_dither_fits.csv.gz")
    dither = dither[dither.mask_rule.eq("strict") & dither.status.eq("fitted")]
    dither = dither.assign(positive=dither[SNR].gt(0), pass5=dither[SNR].ge(5),
                           unlisted_pass5=dither[SNR].ge(5) & dither.listed_contaminants.eq(0))
    counts = dither.groupby(["object_id", "gwa_pos"]).agg(
        usable=(SNR, "size"), pass5=("pass5", "sum"), positive=("positive", "sum"),
        no_list_pass5=("unlisted_pass5", "sum")).unstack(fill_value=0)
    dither_rows = []
    for oid, block in counts.iterrows():
        r0 = int(block.get(("pass5", "RGS000"), 0))
        r180 = int(block.get(("pass5", "RGS180"), 0))
        if min(r0, r180) >= 1:
            dither_rows.append({
                "object_id": int(oid), "rgs000_snr_ge5": r0, "rgs180_snr_ge5": r180,
                "dither_positive": int(block["positive"].sum()),
                "dither_usable": int(block["usable"].sum()),
                "min_direction_no_list_snr_ge5": int(min(
                    block.get(("no_list_pass5", "RGS000"), 0),
                    block.get(("no_list_pass5", "RGS180"), 0),
                )),
            })
    repeat = pd.DataFrame(dither_rows).merge(pilot, on="object_id", validate="one_to_one")
    repeat = repeat.sort_values(
        ["min_direction_no_list_snr_ge5", "rgs000_snr_ge5", "rgs180_snr_ge5", "object_id"],
        ascending=[False, False, False, True],
    )

    hits = fits_table[fits_table.screen_snr.ge(5)]
    ha = (hits[hits.line.eq("Halpha")].sort_values("screen_snr", ascending=False)
          .drop_duplicates("object_id").set_index("object_id"))
    blue = hits[hits.grism.eq("BGS") & hits.line.isin(("Hbeta", "OIII5008"))]
    blue = blue.sort_values("screen_snr", ascending=False).drop_duplicates("object_id")
    widths = ["screen_snr_sigma_20A", "screen_snr_sigma_45A"]
    scores = ha[["grism", "screen_snr", *widths]].add_prefix("ha_")
    scores = scores.join(blue.set_index("object_id")[["line", "screen_snr", *widths]]
                         .add_prefix("blue_")).reset_index()
    scores = scores.rename(columns={"blue_line": "blue_secondary_line",
                                    "blue_screen_snr": "secondary_snr"})
    multi = scores[scores.ha_screen_snr.ge(5) & scores.secondary_snr.ge(5)].merge(
        pilot, on="object_id", validate="one_to_one",
    )
    width_columns = [f"{prefix}_{col}" for prefix in ("ha", "blue") for col in widths]
    multi["both_lines_all_widths_snr_ge5"] = multi[width_columns].ge(5).all(axis=1)
    multi["weakest_snr"] = multi[["ha_screen_snr", "secondary_snr"]].min(axis=1)
    external = pd.read_csv(DAY02 / "validation" / "desi_pairs.csv").query("separation_arcsec <= 0.2")
    external = external[~external.object_id.duplicated(keep=False) & ~external.targetid.duplicated(keep=False)]
    external = external.rename(columns={"z": "desi_z", "targetid": "desi_targetid"})
    external["desi_targetid"] = external.desi_targetid.astype("string")
    multi = multi.merge(external[["object_id", "desi_z", "desi_targetid", "delta_z_norm"]],
                        on="object_id", how="left", validate="one_to_one")
    multi["external_agreement"] = multi.delta_z_norm.abs().le(0.002)
    multi = multi.sort_values(["external_agreement", "weakest_snr", "object_id"],
                              ascending=[False, False, True])
    repeat.to_csv(namespace / "repeatable_halpha.csv", index=False)
    multi.to_csv(namespace / "multi_line_candidates.csv", index=False)
    return repeat, multi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    out = DAY02 / "targets"
    args.cache.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_csv(DAY02 / "observed_results" / "all_morphology_matched.csv.gz")
    image = pd.read_csv(DAY02 / "joint_audit" / "vis_growth_curves.csv.gz",
                        usecols=["object_id", "neighbour_arcsec", "r50_1p5arcsec"])
    pilot = pilot.merge(image, on="object_id", validate="one_to_one")
    selected = pilot[["object_id", "tileid", "ra", "dec", "ra_from_object_id", "dec_from_object_id",
                      "spe_z", "ha_flux", "clean", "neighbour_arcsec", "r50_1p5arcsec"]]
    spectra, files = read_subset(args.cache, selected)
    fits = scan(spectra, selected)
    repeat, multi = candidates(selected, fits, out)
    fits.to_csv(out / "line_screen.csv.gz", index=False,
                compression={"method": "gzip", "mtime": 0}, float_format="%.8g")
    summary = {
        "pilot_objects": len(pilot), "objects_with_spectra_in_partitions": spectra.object_id.nunique(),
        "paired_grism_spectra": len(spectra), "clean_objects_screened": int(
            selected[selected.object_id.isin(spectra.object_id)].clean.sum()),
        "screen_snr_threshold": 5, "repeatable_halpha_objects": len(repeat),
        "multi_line_objects": len(multi), "multi_line_clean_objects": int(multi.clean.sum()),
        "multi_line_desi_agreement": int(multi.external_agreement.sum()),
        "multi_line_separate_grisms": int(multi.ha_grism.eq("RGS").sum()),
        "multi_line_both_lines_all_widths": int(multi.both_lines_all_widths_snr_ge5.sum()),
        "archive_partitions": files,
    }
    (out / "screen_metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
