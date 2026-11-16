"""Audit H-beta and [O III] at the SPE redshifts in both observed NISP grisms."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
import numpy as np
import pandas as pd

from audit_grism_halpha import (
    DAY02, fit_window, get_hats_spectrum, load_matches, read_hats, read_original_blue,
    fetch_archive_file,
)

# Vacuum wavelengths, consistent with the Day 02 SPE H-alpha centre.
LINES = {"Hbeta": 4862.68, "OIII4960": 4960.30, "OIII5008": 5008.24, "Halpha": 6564.61}
SNR_COL = "sigma_30A_formal_snr"


def line_checks(spectra, matches):
    rows = []
    for source in matches:
        oid, tile, z = source["object_id"], source["tile"], source["catalogue_z"]
        for grism in ("BGS", "RGS"):
            spectrum, count = get_hats_spectrum(spectra, oid, tile, grism)
            if count != 1:
                raise ValueError(f"Expected one {grism} spectrum for {oid}, found {count}")
            for name, rest in LINES.items():
                centre = rest * (1 + z)
                for mask_rule in ("unflagged", "allow_low_snr"):
                    fit, _ = fit_window(spectrum, centre, allow_low_snr=mask_rule == "allow_low_snr")
                    rows.append({"object_id": oid, "tileid": tile, "grism": grism, "z_spe": z,
                                 "line": name, "centre_A": centre, "mask_rule": mask_rule, **fit})
    return pd.DataFrame(rows)


def dither_inventory(rows, cache):
    group = {}
    for row in rows:
        group.setdefault(row["s3_key"], []).append(row)
    inventory = []
    for key, matches in group.items():
        path = fetch_archive_file(key, cache / Path(key).name)
        with fits.open(path, memmap=True) as hdus:
            by_prefix = {}
            for index, hdu in enumerate(hdus):
                if "_DITH1D_" in hdu.name and hdu.name.endswith("_SIGNAL"):
                    by_prefix.setdefault(hdu.name.split("_", 1)[0], []).append(index)
            for row in matches:
                prefix = row["hdu_signal"].split("_", 1)[0]
                oid = hdus[f"{prefix}_META"].header["OBJ_ID"]
                if oid != row["object_id"]:
                    raise ValueError(f"FITS identity mismatch for {prefix} in {key}")
                for index in by_prefix.get(prefix, []):
                    hdu = hdus[index]
                    dither_name = hdu.name.removesuffix("_SIGNAL")
                    contaminants = f"{dither_name}_CONTAMINANTS"
                    ids = np.unique(hdus[contaminants].data["OBJ_ID"]).tolist() if contaminants in hdus else []
                    target = row.get("expected_line_wavelength_A")
                    spectrum = pd.DataFrame({
                        name.lower(): np.asarray(hdu.data[name], dtype=float)
                        for name in ("WAVELENGTH", "SIGNAL", "VAR", "QUALITY", "MASK")
                    }).assign(ndith=1)
                    if target is None:
                        status, snr = "historical_example_no_catalogue_redshift", None
                    else:
                        fit, _ = fit_window(spectrum, target)
                        status, snr = fit["status"], fit.get(SNR_COL)
                    inventory.append({
                        "object_id": oid, "dither_hdu": hdu.name, "fits_key": key,
                        "gwa_pos": hdu.header.get("GWA_POS"), "gwa_tilt_deg": hdu.header.get("GWA_TILT"),
                        "listed_contaminants": len(ids),
                        "contaminant_ids": ",".join(str(i) for i in ids), "ha_status": status,
                        "ha_formal_snr": snr,
                    })
    return pd.DataFrame(inventory)


def summarise(lines, dithers):
    strict = lines[lines.mask_rule.eq("unflagged")]
    fits_only = strict[strict.status.eq("fitted")]
    candidates = fits_only[fits_only[SNR_COL] >= 5]
    sets = candidates.groupby("object_id").line.agg(set)
    # For a cross-line consistency candidate, the Halpha complex and an
    # independent transition predicted from the same catalogue z are required.
    consistent = sorted(int(oid) for oid, names in sets.items() if "Halpha" in names and len(names) >= 2)
    candidate_rows = [
        {"object_id": str(row.object_id), "grism": row.grism, "line": row.line,
         "formal_snr": getattr(row, SNR_COL)}
        for row in candidates.itertuples(index=False)
    ]
    relaxed = lines[
        lines.mask_rule.eq("allow_low_snr") & lines.status.eq("fitted") & lines[SNR_COL].ge(5)
    ]
    relaxed_peaks = [
        {"object_id": str(row.object_id), "grism": row.grism, "line": row.line,
         "formal_snr": getattr(row, SNR_COL), "sideband_rms": row.sigma_30A_sideband_rms}
        for row in relaxed.itertuples(index=False)
    ]
    return {
        "matched_objects": int(lines.object_id.nunique()),
        "strict_window_fits": int(len(fits_only)),
        "strict_snr_ge5": candidate_rows,
        "strict_multi_transition_ids": [str(oid) for oid in consistent],
        "allow_low_snr_mask_snr_ge5": relaxed_peaks,
        "blue_dither_rows": int(len(dithers)),
        "blue_dither_rows_with_listed_contaminants": int((dithers.listed_contaminants > 0).sum()),
        "strict_blue_halpha_dither_fits": int(dithers.ha_status.eq("fitted").sum()),
        "max_dither_halpha_formal_snr": float(dithers.ha_formal_snr.max()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DAY02 / "joint_audit")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    matches = load_matches()
    blue, _ = read_original_blue(matches, args.cache)
    hats, _ = read_hats(matches, args.cache)
    for row in matches:
        spectrum, _ = get_hats_spectrum(hats, row["object_id"], row["tile"], "BGS")
        np.testing.assert_allclose(spectrum, blue[row["object_id"]], rtol=2e-5, atol=1e-10)
    lines = line_checks(hats, matches)
    historical_report = DAY02.parents[1] / "2026-11-14-day01" / "analysis" / "real_results" / "real_media_report.json"
    historical = json.loads(historical_report.read_text())["products"]["nisp_spectrum"]
    historical_row = {"s3_key": historical["key"], "hdu_signal": historical["chosen_hdu_name"],
                      "object_id": int(historical["previous_header_object_id"])}
    dithers = dither_inventory([*matches, historical_row], args.cache)
    lines.to_csv(args.output / "line_checks.csv.gz", index=False,
                 compression={"method": "gzip", "mtime": 0}, float_format="%.9g")
    dithers.to_csv(args.output / "blue_dither_inventory.csv.gz", index=False,
                   compression={"method": "gzip", "mtime": 0}, float_format="%.9g")
    summary = summarise(lines, dithers)
    (args.output / "secondary_line_metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
