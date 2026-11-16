"""Compare red-grism coadds and individual exposures for the two leading Hα candidates."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from audit_grism_halpha import DAY02, fit_window, load_matches
from audit_red_dithers import as_spectrum, SNR, FLUX, ERROR

CANDIDATES = (2697432168658721533, 2693965274658805116)
OFFSETS = (-26.8, -13.4, 0.0, 13.4, 26.8)
REST_HA = 6564.61


def inspect_candidate(spectrum, centre):
    fit, plot = fit_window(spectrum, centre, allow_low_snr=True)
    if fit["status"] != "fitted":
        raise ValueError("Previously fitted combined candidate no longer passes selection")
    peak = plot.loc[plot.usable & (plot.wavelength - centre).abs().le(45)].copy()
    peak["excess"] = peak.signal - peak.continuum
    central = peak.loc[peak.excess.idxmax()]
    dropped = spectrum.copy()
    dropped.loc[dropped.wavelength.eq(central.wavelength), "mask"] = 1
    after, _ = fit_window(dropped, centre, allow_low_snr=True)
    results = {"spectral_peak_A": float(central.wavelength),
               "offset_A": float(central.wavelength - centre),
               "peak_mask": int(central["mask"]), "peak_ndith": int(central.ndith),
               "fitted_flux_1e16": float(fit[FLUX]), "fitted_formal_snr": float(fit[SNR]),
               "sideband_rms": float(fit["sigma_30A_sideband_rms"]),
               "after_largest_bin_removed_status": after["status"]}
    if after["status"] == "fitted":
        results["after_largest_bin_removed_flux_1e16"] = float(after[FLUX])
        results["after_largest_bin_removed_snr"] = float(after[SNR])
    return results, plot


def shifted_dither_fits(spectra, centre):
    fits_by_offset = []
    for offset in OFFSETS:
        fits_by_offset.append([fit_window(s, centre + offset)[0] for s in spectra])
    common = np.all([[r["status"] == "fitted" for r in f] for f in fits_by_offset], axis=0)
    values = []
    for offset, fit in zip(OFFSETS, fits_by_offset, strict=True):
        chosen = [row for row, keep in zip(fit, common, strict=True) if keep]
        entry = {"offset_A": offset, "n_common_dithers": len(chosen)}
        if chosen:
            f = np.array([r[FLUX] for r in chosen])
            error = np.array([r[ERROR] * max(1, r["sigma_30A_sideband_rms"]) for r in chosen])
            weight = 1 / error**2
            entry["weighted_flux_1e16"] = float(np.average(f, weights=weight))
            entry["formal_snr"] = float(entry["weighted_flux_1e16"] * np.sqrt(weight.sum()))
        values.append(entry)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fits-cache", type=Path, required=True)
    args = parser.parse_args()
    output = DAY02 / "validation"
    mapping = json.loads((output / "red_fits_matches.json").read_text())
    matches = {r["object_id"]: r for r in load_matches()}
    summary = {}
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.9), layout="constrained")
    for i, oid in enumerate(CANDIDATES):
        key, objects = next((k, v) for k, v in mapping.items() if str(oid) in v)
        prefix = objects[str(oid)]
        centre = matches[oid]["expected_line_wavelength_A"]
        if not np.isclose(centre, REST_HA * (1 + matches[oid]["catalogue_z"])):
            raise ValueError("Hα reference wavelength mismatch")
        with fits.open(args.fits_cache / Path(key).name) as hdus:
            if hdus[f"{prefix}_META"].header["OBJ_ID"] != oid:
                raise ValueError("Catalogue identity mismatch")
            spectrum = as_spectrum(hdus[f"{prefix}_COMBINED1D_SIGNAL"], combined=True)
            dithers = [as_spectrum(h) for h in hdus if h.name.startswith(f"{prefix}_DITH1D_")
                       and h.name.endswith("_SIGNAL")]
        metrics, plot = inspect_candidate(spectrum, centre)
        audit = shifted_dither_fits(dithers, centre)
        metrics["dither_centre_sensitivity"] = audit
        summary[str(oid)] = metrics
        ax = axes[i, 0]
        dx = plot.wavelength - centre
        ax.plot(dx, plot.signal - plot.continuum, color="0.65", lw=1)
        good = plot.usable
        ax.scatter(dx[good], (plot.signal - plot.continuum)[good], s=13, color="#1b6796")
        ax.plot(dx, plot.model - plot.continuum, color="#a9432c", lw=1.2)
        ax.set_title(str(oid), fontsize=10)
        ax.axvline(0, color="0.45", linestyle=":")
        ax.set(xlabel="Offset from SPE Hα (Å)", ylabel="Coadd above continuum")
        ax = axes[i, 1]
        x = [r["offset_A"] for r in audit]
        y = [r.get("formal_snr", np.nan) for r in audit]
        ax.plot(x, y, marker="o", color="#1b6796")
        ax.axhline(0, color="0.55", linestyle=":")
        ax.axvline(0, color="0.55", linestyle=":")
        ax.set(xlabel="Dither template centre shift (Å)", ylabel="Nominal weighted S/N")
        ax.set_title(f"{audit[0]['n_common_dithers']} dithers usable at every shift", fontsize=10)
    fig.savefig(output / "red_candidate_profiles.png", dpi=140)
    plt.close(fig)
    (output / "red_candidate_profiles.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
