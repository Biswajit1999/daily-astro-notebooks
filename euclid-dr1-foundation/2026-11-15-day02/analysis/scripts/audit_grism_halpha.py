"""Fit observed DR1-F combined 1D spectra at catalogue-predicted H-alpha.

The Gaussian is a diagnostic for the unresolved line complex. Its formal
uncertainty uses per-bin variances and does not model spectral covariance.
"""
import argparse
from datetime import date
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

DAY02 = Path(__file__).resolve().parents[1]
FITS_URL = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com/"
HATS = (
    "contributed/dr1/hats/reformatted_catalogs/sir_combined_spectra/"
    "euclid_dr1_reformatted_catalogs_sir_combined_spectra-hats/"
)
# Order and pixel for the 17 fixed Day 02 IDs, from their HATS sky coordinates.
PARTITIONS = {
    (7, 61439): "10da20a9b6fdd91e91e91d52d9720432",
    (8, 163831): "07ef120d6e2994fb4e2167e830cb61b4",
    (8, 163837): "45ba9d62a5133dbf90e031c5e23299b2",
}
SIGNAL_UNIT = "10**-16 erg/s/cm2/Angstrom"
VAR_UNIT = "10**-32 erg2/s2/cm4/Angstrom2"
COLUMNS = ("wavelength", "signal", "var", "quality", "mask", "ndith")
HALF_WINDOW = 250.0
INNER_SIDEBAND = 125.0
CORE = 45.0
WIDTHS = (20.0, 30.0, 45.0)
QUALITY_CUT = 0.8
LOW_SNR_MASK = 2


def load_matches():
    audit = DAY02 / "observed_results" / "matched_spectra" / "matched_spectrum_audit.json"
    matches = [
        match for tile in json.loads(audit.read_text())["examined_tiles"]
        for match in tile["matches"]
    ]
    if len({row["object_id"] for row in matches}) != len(matches):
        raise ValueError("Duplicate object IDs in the Day 02 match list")
    return matches


def fetch_archive_file(key, path):
    if not path.exists():
        tmp = path.with_suffix(".download")
        try:
            with urlopen(FITS_URL + key, timeout=120) as response, tmp.open("wb") as stream:
                shutil.copyfileobj(response, stream)
                size = int(response.headers["Content-Length"])
            if tmp.stat().st_size != size:
                raise OSError(f"Incomplete archive transfer for {key}")
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    return path


def read_original_blue(matches, cache):
    by_key = defaultdict(list)
    for row in matches:
        by_key[row["s3_key"]].append(row)
    with ThreadPoolExecutor(max_workers=4) as executor:
        paths = list(executor.map(lambda key: fetch_archive_file(key, cache / Path(key).name), by_key))
    spectra = {}
    products = []
    for (key, rows), path in zip(by_key.items(), paths, strict=True):
        with fits.open(path, memmap=True) as hdus, path.open("rb") as stream:
            header = hdus[0].header
            if header["LRANGE"] != "BGS":
                raise ValueError(f"Expected blue grism in {key}")
            products.append({
                "key": key, "sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
                "grism": header["LRANGE"], "obsids": header["OBSIDS"],
            })
            for row in rows:
                name = row["hdu_signal"]
                meta = hdus[name.replace("_COMBINED1D_SIGNAL", "_META")]
                hdu = hdus[name]
                if meta.header["OBJ_ID"] != row["object_id"] or header["TILE_ID"] != row["tile"]:
                    raise ValueError(f"FITS identity mismatch in {key}, {name}")
                units = [hdu.columns[col].unit for col in ("WAVELENGTH", "SIGNAL", "VAR")]
                if units != ["Angstrom", SIGNAL_UNIT, VAR_UNIT]:
                    raise ValueError(f"Unexpected FITS units in {key}, {name}: {units}")
                spectra[row["object_id"]] = pd.DataFrame({
                    col: np.asarray(hdu.data[col.upper()], dtype=float) for col in COLUMNS
                })
    return spectra, products


def read_hats(matches, cache):
    ids = pa.array(sorted(row["object_id"] for row in matches))
    files = []
    batches = []
    for (order, pixel), md5 in PARTITIONS.items():
        key = (
            f"{HATS}dataset/Norder={order}/Dir={pixel // 10000 * 10000}/"
            f"Npix={pixel}/part0.snappy.parquet"
        )
        path = fetch_archive_file(key, cache / f"sir_part_{pixel}.parquet")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "md5").hexdigest() != md5:
                raise ValueError(f"Archive checksum mismatch for {key}")
        files.append({"key": key, "archive_md5": md5})
        columns = ["object_id", "tileid", "lrange", "spectrum"]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=columns):
            selected = batch.filter(pc.is_in(batch.column(0), value_set=ids))
            if len(selected):
                batches.append(selected)
    rows = pa.Table.from_batches(batches).to_pandas()
    if set(rows.object_id) != set(ids.to_pylist()):
        raise ValueError("HATS subset does not match the Day 02 object list")
    return rows, files


def get_hats_spectrum(rows, object_id, tile, grism):
    found = rows[(rows.object_id == object_id) & (rows.tileid == tile) & (rows.lrange == grism)]
    if len(found) != 1:
        return None, len(found)
    return pd.DataFrame(found.iloc[0].spectrum).loc[:, COLUMNS].astype(float), 1


def hats_to_fits_units(hats_blue, original_blue):
    """Use a blue-grism FITS reference to check storage scaling of HATS values."""
    native_columns = ["signal", "var"]
    archive = hats_blue[native_columns].to_numpy()
    original = original_blue[native_columns].to_numpy()
    for signal_scale in (1.0, 1e16):
        scales = np.array([signal_scale, signal_scale**2])
        if np.allclose(archive * scales, original, rtol=2e-5, atol=1e-10, equal_nan=True):
            return scales
    raise ValueError("HATS blue signal and variance disagree with original FITS")


def fit_window(spectrum, centre, quality=QUALITY_CUT, allow_low_snr=False):
    spec = spectrum.sort_values("wavelength").reset_index(drop=True)
    wavelength = spec.wavelength.to_numpy()
    if not np.isfinite(wavelength).all() or np.any(np.diff(wavelength) <= 0):
        raise ValueError("Invalid spectral wavelength grid")
    offsets = wavelength - centre
    window = np.abs(offsets) <= HALF_WINDOW
    core = np.abs(offsets) <= CORE
    finite = np.isfinite(spec[["signal", "var", "quality"]]).all(axis=1)
    masks = spec["mask"].isin((0, LOW_SNR_MASK)) if allow_low_snr else spec["mask"].eq(0)
    usable = finite & (spec["var"] > 0) & masks
    usable &= (spec["quality"] > quality) & (spec.ndith > 0)
    good = usable.to_numpy()
    left = (offsets < -INNER_SIDEBAND) & window & good
    right = (offsets > INNER_SIDEBAND) & window & good
    row = {
        "wavelength_min_A": wavelength[0], "wavelength_max_A": wavelength[-1],
        "bins_in_core": int(core.sum()), "usable_core": int((core & good).sum()),
        "usable_blue_sideband": int(left.sum()), "usable_red_sideband": int(right.sum()),
        "core_bins_masked_low_snr_only": int((core & spec["mask"].eq(LOW_SNR_MASK)).sum()),
        "median_ndith_in_usable_core": (
            float(np.median(spec.ndith[core & good])) if (core & good).any() else None
        ),
    }

    if not wavelength[0] <= centre <= wavelength[-1]:
        row["status"] = "outside_wavelength_range"
    elif wavelength[0] > centre - HALF_WINDOW or wavelength[-1] < centre + HALF_WINDOW:
        row["status"] = "window_truncated"
    elif ((core & good).sum() < max(5, 0.6 * core.sum())
          or not (core & good & (offsets < 0)).any()
          or not (core & good & (offsets > 0)).any()
          or min(left.sum(), right.sum()) < 5):
        row["status"] = "insufficient_usable_bins"
    else:
        row["status"] = "fitted"
    plot = spec.loc[window].assign(usable=good[window])
    if row["status"] != "fitted":
        return row, plot

    fit = window & good
    x = offsets[fit]
    y = spec.signal.to_numpy()[fit]
    noise = np.sqrt(spec["var"].to_numpy()[fit])
    for width in WIDTHS:
        # Unit-integral Gaussian. Its fitted amplitude is the integrated flux.
        template = np.exp(-0.5 * (x / width)**2) / (np.sqrt(2 * np.pi) * width)
        design = np.column_stack((np.ones_like(x), x / HALF_WINDOW, template))
        weighted = design / noise[:, None]
        coefficients, _, rank, _ = np.linalg.lstsq(weighted, y / noise, rcond=None)
        if rank != 3:
            raise ValueError("Degenerate continuum and line fit")
        standard_error = np.sqrt(np.linalg.inv(weighted.T @ weighted)[2, 2])
        model = design @ coefficients
        residual = (y - model) / noise
        side = np.abs(x) > INNER_SIDEBAND
        prefix = f"sigma_{int(width)}A"
        row[f"{prefix}_flux_1e16"] = coefficients[2]
        row[f"{prefix}_formal_snr"] = coefficients[2] / standard_error
        row[f"{prefix}_flux_se_1e16"] = standard_error
        row[f"{prefix}_sideband_rms"] = np.sqrt(np.mean(residual[side]**2))
        row[f"{prefix}_reduced_chi2"] = np.sum(residual**2) / (len(x) - 3)
        if width == 30.0:
            x_plot = offsets[window]
            continuum = coefficients[0] + coefficients[1] * x_plot / HALF_WINDOW
            template_plot = np.exp(-0.5 * (x_plot / width)**2) / (np.sqrt(2 * np.pi) * width)
            plot = plot.assign(continuum=continuum, model=continuum + coefficients[2] * template_plot)
    return row, plot


def plot_pairs(panels, output):
    paired_ids = sorted(oid for oid, grisms in panels.items() if len(grisms) == 2)
    if not paired_ids:
        return
    fig, axes = plt.subplots(len(paired_ids), 2, figsize=(10, 2.6 * len(paired_ids)),
                             sharex=True, squeeze=False, layout="constrained")
    for pair_axes, oid in zip(axes, paired_ids, strict=True):
        for ax, grism in zip(pair_axes, ("BGS", "RGS"), strict=True):
            centre, result, frame = panels[oid][grism]
            x = frame.wavelength - centre
            ax.plot(x, frame.signal.where(frame.ndith > 0), color="0.68", linewidth=1)
            keep = frame.usable
            ax.scatter(x[keep], frame.loc[keep, "signal"], color="#1d5f92", s=10)
            ax.axvline(0, color="0.35", linestyle=":", linewidth=1)
            title = result["status"].replace("_", " ")
            if "model" in frame:
                ax.plot(x, frame.model, color="#a73f28", linewidth=1.5)
                ax.plot(x, frame.continuum, color="#a73f28", linestyle="--", linewidth=1)
                title = f'formal S/N {result["sigma_30A_formal_snr"]:+.1f}'
            ax.set_title(f"{oid} · {grism} · {title}", fontsize=9)
    fig.supxlabel("Offset from catalogue-predicted Hα (Å)")
    fig.supylabel("Signal (10⁻¹⁶ erg s⁻¹ cm⁻² Å⁻¹)")
    fig.savefig(output / "paired_grism_windows.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DAY02 / "spectral_audit")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    matches = load_matches()
    blue, products = read_original_blue(matches, args.cache)
    hats, hats_files = read_hats(matches, args.cache)
    results = []
    scales = None
    panels = defaultdict(dict)
    for match in matches:
        oid, tile = match["object_id"], match["tile"]
        # The same SPE redshift is used to position both grism templates.
        centre = match["expected_line_wavelength_A"]
        hats_blue, blue_rows = get_hats_spectrum(hats, oid, tile, "BGS")
        if hats_blue is None:
            raise ValueError(f"Expected one HATS blue row for {oid}, found {blue_rows}")
        if scales is None:
            scales = hats_to_fits_units(hats_blue, blue[oid])
        hats_blue[["signal", "var"]] *= scales
        np.testing.assert_allclose(blue[oid], hats_blue, rtol=2e-5, atol=1e-10, equal_nan=True)
        red, red_rows = get_hats_spectrum(hats, oid, tile, "RGS")
        if red is not None:
            red[["signal", "var"]] *= scales
        for grism, spectrum in (("BGS", blue[oid]), ("RGS", red)):
            row = {
                "object_id": oid, "tileid": tile, "grism": grism,
                "z_spe": match["catalogue_z"], "expected_wavelength_A": centre,
                "spe_snr": match["catalogue_Halpha_snr"],
                "spe_flux_1e16": match["catalogue_Halpha_flux"] / 1e-16,
                "hats_rows_same_tile": blue_rows if grism == "BGS" else red_rows,
            }
            if spectrum is None:
                row["status"] = "missing_hats_row" if red_rows == 0 else "ambiguous_hats_rows"
            else:
                fit, plot = fit_window(spectrum, centre)
                row.update(fit)
                if grism == "RGS":
                    quality_fit, _ = fit_window(spectrum, centre, quality=0.5)
                    row["quality_gt_0_5_status"] = quality_fit["status"]
                    row["quality_gt_0_5_snr"] = quality_fit.get("sigma_30A_formal_snr")
                    low_snr_fit, _ = fit_window(spectrum, centre, allow_low_snr=True)
                    row["allow_low_snr_mask_status"] = low_snr_fit["status"]
                    row["allow_low_snr_mask_snr"] = low_snr_fit.get("sigma_30A_formal_snr")
                    row["allow_low_snr_mask_flux_1e16"] = low_snr_fit.get("sigma_30A_flux_1e16")
                if not plot.empty and blue[oid].wavelength.min() <= centre <= blue[oid].wavelength.max():
                    panels[oid][grism] = (centre, row, plot)
            results.append(row)
    frame = pd.DataFrame(results)
    frame.to_csv(args.output / "line_fits.csv", index=False, float_format="%.9g")
    summary = {
        "data_release": "Euclid DR1-Foundation",
        "run_date": date.today().isoformat(),
        "source_matches": len(matches), "fits_templates_sigma_A": WIDTHS,
        "half_window_A": HALF_WINDOW, "core_half_width_A": CORE,
        "inner_sideband_A": INNER_SIDEBAND, "quality_strictly_greater_than": QUALITY_CUT,
        "fits_signal_unit": SIGNAL_UNIT, "fits_variance_unit": VAR_UNIT,
        "hats_to_fits_signal_variance_factors": scales.tolist(),
        "archive_url": FITS_URL,
        "blue_fits_hats_matches": len(blue), "fits_products": products, "hats_products": hats_files,
        "package_versions": {
            pkg: version(pkg) for pkg in ("astropy", "numpy", "pandas", "pyarrow", "matplotlib")
        },
        "red_grism_allow_low_snr_mask_status_counts": (
            frame[frame.grism == "RGS"].allow_low_snr_mask_status.value_counts().to_dict()
        ),
        "status_counts": {
            grism: group.status.value_counts().to_dict() for grism, group in frame.groupby("grism")
        },
    }
    (args.output / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    plot_pairs(panels, args.output)
    print(json.dumps(summary["status_counts"], indent=2))


if __name__ == "__main__":
    main()
