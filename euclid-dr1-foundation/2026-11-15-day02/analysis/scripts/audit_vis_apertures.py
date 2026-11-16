"""Measure VIS aperture growth curves directly on released MER mosaics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys

from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

DAY02 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY02.parents[1] / "2026-11-14-day01" / "analysis" / "scripts"))
from analyse_day01 import test_effect
from audit_grism_halpha import fetch_archive_file

# Angular radii are in arcsec. Main size is half the signed flux within 1.5 arcsec.
RADII = np.arange(0.1, 2.01, 0.1)
ANNULUS = (2.5, 3.5)
BANDS = ("VIS", "NIR-Y", "NIR-J", "NIR-H")
VIS_INVALID = 1
HISTORICAL_IMAGE_IDS = {2697974927659867240, 2696558115658832112}


def image_array(hdu, bounds):
    x0, y0, x1, y1 = bounds
    # section handles the unsigned integer scaling present in flag mosaics.
    return hdu.section[y0:y1, x0:x1]


def stamp_bounds(cx, cy, shape, halfwidth):
    x0 = int(np.floor(cx)) - halfwidth
    y0 = int(np.floor(cy)) - halfwidth
    x1, y1 = x0 + 2 * halfwidth + 2, y0 + 2 * halfwidth + 2
    if x0 < 0 or y0 < 0 or x1 > shape[1] or y1 > shape[0]:
        return None
    return x0, y0, x1, y1


def measure_image(image, flags, cx, cy, scale):
    y, x = np.indices(image.shape)
    r = np.hypot(x - cx, y - cy) * scale
    finite = np.isfinite(image)
    if flags is not None:
        finite &= (flags & VIS_INVALID) == 0
    inner = r <= 2
    annulus = (r >= ANNULUS[0]) & (r <= ANNULUS[1])
    valid_bg = annulus & finite
    result = {
        "usable_fraction_r2": float(finite[inner].mean()),
        "usable_fraction_annulus": float(finite[annulus].mean()),
    }
    if result["usable_fraction_r2"] < 0.98 or result["usable_fraction_annulus"] < 0.80:
        result["image_status"] = "pixel_coverage"
        return result
    background = np.median(image[valid_bg])
    residual = image - background
    sigma = 1.4826 * np.median(np.abs(residual[valid_bg]))
    profile = np.array([residual[(r <= radius) & finite].sum(dtype=float) for radius in RADII])
    result.update({"local_sky": float(background), "annulus_mad_sigma": float(sigma)})
    for target, suffix in ((1.0, "1arcsec"), (1.5, "1p5arcsec"), (2.0, "2arcsec")):
        index = np.argmin(np.abs(RADII - target))
        total = profile[index]
        aperture_n = np.count_nonzero((r <= target) & finite)
        result[f"flux_{suffix}"] = total
        if total <= 0 or sigma <= 0:
            continue
        # Adjacent pixels in the resampled mosaic are correlated. This statistic
        # is a brightness screen, not a calibrated significance estimate.
        result[f"nominal_aperture_snr_{suffix}"] = total / (sigma * np.sqrt(aperture_n))
        above = np.flatnonzero(profile[:index + 1] >= 0.5 * total)
        first = int(above[0])
        r0, f0 = (0.0, 0.0) if first == 0 else (RADII[first - 1], profile[first - 1])
        r1, f1 = RADII[first], profile[first]
        result[f"r50_{suffix}"] = float(r0 + (r1 - r0) * (0.5 * total - f0) / (f1 - f0))
    result["image_status"] = "measured" if "r50_1p5arcsec" in result else "nonpositive_profile"
    return result


def unit_vectors(ra, dec):
    lon, lat = np.deg2rad(ra), np.deg2rad(dec)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def neighbour_distances(table, targets):
    # Search the complete tile catalogue, including sources with no SPE match.
    ra, dec = table["RIGHT_ASCENSION"], table["DECLINATION"]
    finite = np.isfinite(ra) & np.isfinite(dec)
    ids = table["OBJECT_ID"][finite]
    if not set(targets.object_id).issubset(ids):
        raise ValueError("Targets missing from original MER tile catalogue")
    tree = cKDTree(unit_vectors(ra[finite], dec[finite]))
    points = unit_vectors(targets.ra.to_numpy(), targets.dec.to_numpy())
    distance, index = tree.query(points, k=2)
    if not np.array_equal(ids[index[:, 0]], targets.object_id):
        raise ValueError("Nearest MER source differs from the selected exact ID")
    return np.rad2deg(2 * np.arcsin(distance[:, 1] / 2)) * 3600


def prepare_inputs(cache, products):
    def fetch(item):
        label, info = item
        key = info["key"]
        path = fetch_archive_file(key, cache / Path(key).name)
        if path.stat().st_size != info["size"]:
            raise OSError(f"Unexpected size for {key}")
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        return label, path, checksum
    with ThreadPoolExecutor(max_workers=6) as pool:
        return {label: (path, checksum) for label, path, checksum in pool.map(fetch, products.items())}


def catalog_checksums():
    inputs = json.loads((DAY02 / "observed_results" / "provenance.json").read_text())["inputs"]
    return {item["tile"]: item["sha256"] for item in inputs if item["kind"] == "MER_FINAL-CAT FITS"}


def process_tile(tile, targets, paths, spectra_ids):
    rows, stamps = [], {}
    with ExitStack() as stack:
        def load(label):
            path = paths[f"{tile}/{label}"][0]
            return stack.enter_context(fits.open(path, memmap=True))
        catalog_label = f"{tile}/catalog"
        expected = catalog_checksums()[tile]
        if paths[catalog_label][1] != expected:
            raise ValueError(f"MER catalogue checksum differs from Day 02 for tile {tile}")
        catalog = load("catalog")[1].data
        targets = targets.assign(neighbour_arcsec=neighbour_distances(catalog, targets))
        science = load("VIS/science")[0]
        flags = load("VIS/flag")[0]
        wcs = WCS(science.header)
        flag_wcs = WCS(flags.header)
        xy = wcs.world_to_pixel_values(targets.ra.to_numpy(), targets.dec.to_numpy())
        np.testing.assert_allclose(
            xy, flag_wcs.world_to_pixel_values(targets.ra.to_numpy(), targets.dec.to_numpy()),
            rtol=0, atol=0.01,
        )
        scale = float(np.mean(proj_plane_pixel_scales(wcs)) * 3600)
        if not np.isclose(scale, 0.1, atol=0.0001):
            raise ValueError(f"Unexpected VIS pixel scale {scale}")
        nir = {band: load(f"{band}/science")[0] for band in BANDS[1:]
               if f"{tile}/{band}/science" in paths}
        for i, target in enumerate(targets.itertuples(index=False)):
            cx, cy = xy[0][i], xy[1][i]
            row = {"object_id": target.object_id, "tileid": tile,
                   "neighbour_arcsec": target.neighbour_arcsec,
                   "vis_pixel_scale_arcsec": scale}
            bounds = stamp_bounds(cx, cy, science.shape, int(np.ceil(ANNULUS[1] / scale)) + 2)
            if bounds is None:
                row["image_status"] = "tile_edge"
            else:
                vis = image_array(science, bounds)
                flag = image_array(flags, bounds)
                row.update(measure_image(vis, flag, cx - bounds[0], cy - bounds[1], scale))
                if target.object_id in spectra_ids:
                    stamps[target.object_id] = {"VIS": (vis.copy(), cx - bounds[0], cy - bounds[1])}
                    for band, hdu in nir.items():
                        nwcs = WCS(hdu.header)
                        nx, ny = nwcs.world_to_pixel_values(target.ra, target.dec)
                        bscale = float(np.mean(proj_plane_pixel_scales(nwcs)) * 3600)
                        band_bounds = stamp_bounds(nx, ny, hdu.shape, int(np.ceil(3.5 / bscale)) + 2)
                        if band_bounds is not None:
                            image = image_array(hdu, band_bounds)
                            sx, sy = nx - band_bounds[0], ny - band_bounds[1]
                            stamps[target.object_id][band] = (image.copy(), sx, sy)
                            metrics = measure_image(image, None, sx, sy, bscale)
                            for key in ("r50_1p5arcsec", "nominal_aperture_snr_1p5arcsec", "image_status"):
                                row[f"{band}_{key}"] = metrics.get(key)
            rows.append(row)
    return rows, stamps


def conditional_effect(frame, outcome):
    sample = frame.sort_values("object_id").copy()
    sample["log_aperture_radius_pix"] = np.log10(sample[outcome])
    sample["log_halpha_flux"] = np.log10(sample.ha_flux)
    sample["log_vis_aper_flux_uJy"] = np.log10(sample.flux_vis_2fwhm_aper)
    return {"n_input": len(sample), **test_effect(sample, seed=20261115)}


def analyser(sample):
    outcomes = ("kron_radius", "r50_1arcsec", "r50_1p5arcsec", "r50_2arcsec")
    usable = sample.loc[
        sample.clean & sample.image_status.eq("measured")
        & (sample.nominal_aperture_snr_1p5arcsec >= 15)
        & sample[list(outcomes)].gt(0).all(axis=1)
    ]
    sensitivity = {}
    for min_distance in (3.5, 2.5, 2.0, 0.0):
        subset = usable.loc[usable.neighbour_arcsec >= min_distance]
        sensitivity[str(min_distance)] = {
            "selected": len(subset),
            "effects": {name: conditional_effect(subset, name) for name in outcomes},
        }
    return {
        "archive_matched": len(sample), "strict_imaging_catalogue": int(sample.clean.sum()),
        "image_status": sample.image_status.value_counts().to_dict(),
        "usable_before_neighbour_cut": len(usable),
        "minimum_neighbour_distance_arcsec": sensitivity,
    }


def make_montage(stamps, output):
    ids = sorted(stamps)
    fig, axes = plt.subplots(len(ids), len(BANDS), squeeze=False,
                             figsize=(7.2, 1.30 * len(ids)), layout="constrained")
    for row, object_id in enumerate(ids):
        images = stamps[object_id]
        for col, band in enumerate(BANDS):
            ax = axes[row, col]
            stamp = images.get(band)
            if stamp is not None:
                data, cx, cy = stamp
                lo, hi = np.nanpercentile(data, [5, 99.5])
                cut = np.clip((data - lo) / max(hi - lo, np.finfo(float).eps), 0, 1)
                ax.imshow(np.sqrt(cut), origin="lower", cmap="gray_r")
                ax.plot(cx, cy, "+", color="tab:red", markersize=4)
                ax.set_xlim(cx - 22, cx + 22)
                ax.set_ylim(cy - 22, cy + 22)
            if row == 0:
                ax.set_title(band, fontsize=9)
            if col == 0:
                ax.set_ylabel(str(object_id), fontsize=6, rotation=0, ha="right")
            ax.set_xticks([])
            ax.set_yticks([])
    fig.savefig(output / "matched_vis_nir.png", dpi=80)
    plt.close(fig)


def make_effect_plot(summary, output):
    fig, ax = plt.subplots(figsize=(7.3, 3.8), layout="constrained")
    distances = summary["minimum_neighbour_distance_arcsec"]
    outcomes = {"kron_radius": ("MER Kron radius", "#b84f36"),
                "r50_1p5arcsec": ("Pixel-based VIS radius", "#1f6490")}
    for (name, (label, color)), offset in zip(outcomes.items(), (-0.10, 0.10), strict=True):
        for i, (_, group) in enumerate(distances.items()):
            effect = group["effects"][name]
            if effect["status"] != "COMPUTED":
                continue
            value = effect["weighted_median_log10_radius_difference"]
            low, high = effect["bootstrap_95_interval_log10"]
            ax.errorbar(value, i + offset, xerr=[[value - low], [high - value]],
                        fmt="o", color=color, capsize=3, label=label if i == 1 else None)
    ax.axvline(0, linestyle=":", color="0.45")
    ax.set_yticks(range(len(distances)), [
        f"≥ {distance}″ · {group['selected']} objects" for distance, group in distances.items()
    ])
    ax.set(xlabel="High minus low Hα median log-radius contrast (dex)",
           ylabel="Nearest catalogue neighbour")
    ax.text(0.02, 0, "Insufficient sample", va="center")
    ax.set_ylim(len(distances) - 0.55, -0.45)
    ax.legend(loc="upper right", frameon=False)
    fig.savefig(output / "vis_radius_contrasts.png", dpi=130)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DAY02 / "joint_audit")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    products = json.loads((DAY02 / "joint_audit" / "image_products.json").read_text())
    paths = prepare_inputs(args.cache, products)
    data = DAY02 / "observed_results"
    matched = pd.read_csv(data / "all_morphology_matched.csv.gz")
    spectral_audit = json.loads((data / "matched_spectra" / "matched_spectrum_audit.json").read_text())
    spectra_ids = {r["object_id"] for t in spectral_audit["examined_tiles"] for r in t["matches"]}
    spectra_ids |= HISTORICAL_IMAGE_IDS
    rows, stamps = [], {}
    for tile, targets in matched.groupby("tileid"):
        measures, tile_stamps = process_tile(tile, targets, paths, spectra_ids)
        rows.extend(measures)
        stamps.update(tile_stamps)
        print(f"{tile}: {len(measures)} objects", flush=True)
    result = matched.merge(pd.DataFrame(rows), on=["object_id", "tileid"], validate="one_to_one")
    if len(result) != len(matched):
        raise ValueError("Image measurement output lost objects")
    measurement_cols = list(pd.DataFrame(rows).columns)
    result[measurement_cols].to_csv(args.output / "vis_growth_curves.csv.gz", index=False,
                                    compression={"method": "gzip", "mtime": 0}, float_format="%.8g")
    summary = analyser(result)
    summary["products"] = {label: {"key": products[label]["key"], "sha256": sha}
                           for label, (_, sha) in paths.items()}
    summary["vis_invalid_flag_bit"] = VIS_INVALID
    summary["multiband_images"] = {str(oid): sorted(bands) for oid, bands in stamps.items()}
    (args.output / "vis_effects.json").write_text(json.dumps(summary, indent=2) + "\n")
    make_montage(stamps, args.output)
    make_effect_plot(summary, args.output)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("products", "multiband_images")}, indent=2))


if __name__ == "__main__":
    main()
