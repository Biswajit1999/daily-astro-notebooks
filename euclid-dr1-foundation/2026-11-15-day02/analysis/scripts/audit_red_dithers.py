"""Check whether Hα persists across individual DR1-F red-grism extractions."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from astropy.io import fits
import numpy as np
import pandas as pd

from audit_grism_halpha import (
    COLUMNS, DAY02, SIGNAL_UNIT, VAR_UNIT, fetch_archive_file, fit_window,
    get_hats_spectrum, load_matches, read_hats,
)

SNR = "sigma_30A_formal_snr"
FLUX = "sigma_30A_flux_1e16"
ERROR = "sigma_30A_flux_se_1e16"
RMS = "sigma_30A_sideband_rms"


def as_spectrum(hdu, combined=False):
    units = [hdu.columns[col].unit for col in ("WAVELENGTH", "SIGNAL", "VAR")]
    if units != ["Angstrom", SIGNAL_UNIT, VAR_UNIT]:
        raise ValueError(f"Unexpected units in {hdu.name}: {units}")
    fields = COLUMNS if combined else COLUMNS[:-1]
    data = pd.DataFrame({key: np.asarray(hdu.data[key.upper()], dtype=float) for key in fields})
    return data if combined else data.assign(ndith=1)


def inspect_product(key, mapping, matches, hats, cache, rows):
    path = fetch_archive_file(key, cache / Path(key).name)
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    with fits.open(path, memmap=True) as hdus:
        header = hdus[0].header
        if header["LRANGE"] != "RGS":
            raise ValueError(f"Wrong grism for {key}")
        extensions = defaultdict(list)
        for index, hdu in enumerate(hdus):
            if "_DITH1D_" in hdu.name and hdu.name.endswith("_SIGNAL"):
                extensions[hdu.name.split("_", 1)[0]].append(index)
        for identifier, prefix in mapping.items():
            oid = int(identifier)
            match = matches[oid]
            if (hdus[f"{prefix}_META"].header["OBJ_ID"] != oid
                    or header["TILE_ID"] != match["tile"]):
                raise ValueError(f"FITS object or tile mismatch for {oid}")
            hats_red, count = get_hats_spectrum(hats, oid, match["tile"], "RGS")
            if count != 1:
                raise ValueError(f"Expected exactly one cached HATS red spectrum for {oid}")
            combined = as_spectrum(hdus[f"{prefix}_COMBINED1D_SIGNAL"], combined=True)
            np.testing.assert_allclose(combined, hats_red, rtol=2e-5, atol=1e-10, equal_nan=True)
            for index in extensions[prefix]:
                hdu = hdus[index]
                spectrum = as_spectrum(hdu)
                name = hdu.name.removesuffix("_SIGNAL")
                cont_hdu = f"{name}_CONTAMINANTS"
                ids = sorted(set(hdus[cont_hdu].data["OBJ_ID"].tolist())) if cont_hdu in hdus else []
                for rule, allow_warning in (("strict", False), ("allow_low_snr", True)):
                    fit, _ = fit_window(spectrum, match["expected_line_wavelength_A"],
                                        allow_low_snr=allow_warning)
                    rows.append({
                        "object_id": oid, "tileid": match["tile"], "fits_key": key,
                        "dither_hdu": hdu.name, "gwa_pos": hdu.header["GWA_POS"],
                        "gwa_tilt_deg": hdu.header["GWA_TILT"], "mask_rule": rule,
                        "centre_A": match["expected_line_wavelength_A"],
                        "listed_contaminants": len(ids),
                        "contaminant_ids": ",".join(map(str, ids)), **fit,
                    })
    return {"key": key, "sha256": checksum, "objects_checked_against_hats": len(mapping)}


def orientation_summary(fits_table):
    results = []
    for (oid, rule, grism, tilt), block in fits_table.groupby(
        ["object_id", "mask_rule", "gwa_pos", "gwa_tilt_deg"], sort=True
    ):
        valid = block[block.status.eq("fitted")]
        row = {"object_id": str(oid), "mask_rule": rule, "gwa_pos": grism,
               "gwa_tilt_deg": int(tilt), "dithers_total": len(block), "dithers_fitted": len(valid)}
        if len(valid):
            # Inflate variance by sideband scatter where it exceeds formal noise.
            # The combined statistic remains descriptive because covariance is unknown.
            se = valid[ERROR] * np.maximum(1.0, valid[RMS])
            weight = 1 / se**2
            mean = np.average(valid[FLUX], weights=weight)
            row.update({
                "positive_dithers": int(valid[FLUX].gt(0).sum()),
                "max_dither_formal_snr": float(valid[SNR].max()),
                "weighted_flux_1e16": float(mean),
                "nominal_weighted_snr": float(mean * np.sqrt(weight.sum())),
                "unlisted_contaminants_dithers": int(valid.listed_contaminants.eq(0).sum()),
            })
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fits-cache", type=Path, required=True)
    parser.add_argument("--hats-cache", type=Path, required=True)
    args = parser.parse_args()
    args.fits_cache.mkdir(parents=True, exist_ok=True)
    args.hats_cache.mkdir(parents=True, exist_ok=True)
    output = DAY02 / "validation"
    mapping = json.loads((output / "red_fits_matches.json").read_text())
    matches = {r["object_id"]: r for r in load_matches()}
    hats, _ = read_hats(list(matches.values()), args.hats_cache)
    rows, products = [], []
    for key, objects in mapping.items():
        products.append(inspect_product(key, objects, matches, hats, args.fits_cache, rows))
    fits_table = pd.DataFrame(rows)
    identity = ["object_id", "dither_hdu", "mask_rule"]
    if fits_table.duplicated(identity).any():
        raise ValueError("Repeated dither rows")
    strict = fits_table[fits_table.mask_rule.eq("strict")]
    result = {
        "expected_objects": len(matches),
        "matched_objects": int(strict.object_id.nunique()),
        "missing_object_ids": [str(oid) for oid in sorted(matches.keys() - set(strict.object_id))],
        "red_dithers": len(strict),
        "red_dithers_with_listed_contaminants": int(strict.listed_contaminants.gt(0).sum()),
        "statuses": {key: block.status.value_counts().to_dict()
                     for key, block in fits_table.groupby("mask_rule")},
        "original_fits": products,
        "orientation_fits": orientation_summary(fits_table),
    }
    fits_table.to_csv(output / "red_dither_fits.csv.gz", index=False,
                      compression={"method": "gzip", "mtime": 0}, float_format="%.8g")
    (output / "red_dither_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("original_fits", "orientation_fits")},
                     indent=2))


if __name__ == "__main__":
    main()
