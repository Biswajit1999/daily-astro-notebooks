"""Measure selection effects on an optical-colour tally in four ACT cluster fields."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy_healpix import HEALPix
import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
COVERAGE_STUDY = ROOT.parent / "act-cluster-coverage"
sys.path.insert(0, str(COVERAGE_STUDY))
from analyze import angular_grid, samples  # noqa: E402

PRIMARY = (0.80, 23.0, 0.80)  # minimum map weight, maximum i AB, minimum r-i
SELECTIONS = ("optical", "common_footprint", "quality_j_detection")
HEALPIX = HEALPix(nside=16384, order="nested")


def get_file(url, folder):
    path = folder / url.rsplit("/", 1)[-1]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(".part")
        with urlopen(url, timeout=90) as reply, temporary.open("wb") as handle:
            shutil.copyfileobj(reply, handle)
        temporary.replace(path)
    with path.open("rb") as handle:
        return path, file_digest(handle, "sha256").hexdigest()


def mask_at(path, tile, band, cells):
    with fits.open(path) as hdus:
        assert hdus[0].header["FILTER"] == band and hdus[0].header["TILEID"] == tile
        hdu = hdus["COVERAGE_MASK"]
        assert hdu.header["ORDERING"] == "NESTED" and hdu.header["NSIDE"] == HEALPIX.nside
        table = hdu.data
        order = np.argsort(table["PIXEL"])
        pixels = table["PIXEL"][order]
        assert np.all(np.diff(pixels) > 0)
        index = np.minimum(np.searchsorted(pixels, cells), len(pixels) - 1)
        return np.where(pixels[index] == cells, table["WEIGHT"][order[index]], np.nan)


def flux(data, band):
    value = np.array(data[f"FLUX_{band}_2FWHM_APER"], dtype=float)
    error = np.array(data[f"FLUXERR_{band}_2FWHM_APER"], dtype=float)
    qualified = (np.isfinite(value) & np.isfinite(error) & (error > 0)
                 & (value >= 5 * error) & (data[f"FLAG_{band}"] == 0))
    return value, qualified


def prepare(cluster, files):
    centre = SkyCoord(cluster["ra_deg"], cluster["dec_deg"], unit="deg")
    theta = cluster["theta500_arcmin"]
    with fits.open(files["MER"], memmap=True) as hdus:
        data = hdus[1].data
        sky = SkyCoord(data["RIGHT_ASCENSION"], data["DECLINATION"], unit="deg")
        radius = centre.separation(sky).arcmin / theta
        annulus = (radius >= 1) & (radius < 2)
        data = data[annulus]
        sky = sky[annulus]
        assert np.all(data["TILE_INDEX"] == cluster["tile_id"])
        assert len(np.unique(data["OBJECT_ID"])) == len(data)
        _, vis_ok = flux(data, "VIS")
        r, r_ok = flux(data, "R_EXT_DECAM")
        i, i_ok = flux(data, "I_EXT_DECAM")
        _, j_ok = flux(data, "J")
        quality = (
            (data["VIS_DET"] == 1) & (data["DET_QUALITY_FLAG"] == 0)
            & (data["SPURIOUS_FLAG"] == 0) & (data["POINT_LIKE_FLAG"] != 1)
            & vis_ok & r_ok & i_ok
        )
        with np.errstate(invalid="ignore", divide="ignore"):
            colour = -2.5 * np.log10(r / i)
            i_mag = 23.9 - 2.5 * np.log10(i)
        ids = data["OBJECT_ID"].astype(np.int64)
    position_cells = HEALPIX.lonlat_to_healpix(sky.ra, sky.dec)
    draw = samples(15, 663)
    lon, lat = angular_grid(np.array([centre.ra.rad]), np.array([centre.dec.rad]),
                            np.array([theta]), (1, 2), draw)
    area_cells = HEALPIX.lonlat_to_healpix(lon.ravel(), lat.ravel())
    cells = np.concatenate((position_cells, area_cells))
    masks = {band: mask_at(files[band], cluster["tile_id"], band, cells)
             for band in ("VIS", "DECAM_r", "DECAM_i", "NIR_J")}
    split = len(ids)
    assert all(np.isfinite(weight[split:]).all() for weight in masks.values())
    return {
        "object_count": split, "quality": quality, "colour": colour, "i_mag": i_mag,
        "j_ok": j_ok,
        "sectors": (centre.position_angle(sky).degree / 45).astype(int) % 8,
        "optical_weight": np.minimum.reduce([masks[key] for key in ("VIS", "DECAM_r", "DECAM_i")]),
        "j_weight": masks["NIR_J"],
    }


def wilson(k, n):
    """A descriptive Wilson interval, conditional on catalogue entries."""
    if not n:
        return None
    z = norm.ppf(.975)
    frac = k / n
    midpoint = frac + z**2 / (2 * n)
    width = z * np.sqrt(frac * (1 - frac) / n + z**2 / (4 * n**2))
    return [float((midpoint - width) / (1 + z**2 / n)),
            float((midpoint + width) / (1 + z**2 / n))]


def fraction(denominator, red):
    n, k = int(denominator.sum()), int((denominator & red).sum())
    return {"red": k, "count": n, "fraction": k / n if n else None, "wilson95": wilson(k, n)}


def paired_difference(original, subset, red, sectors):
    n, m = int(original.sum()), int(subset.sum())
    if not m:
        return {"delta": None, "sector_bootstrap95": None, "max_abs_delta": None}
    assert not np.any(subset & ~original)
    # Resample paired 45-degree sectors, retaining angular clustering within each sector.
    parts = [np.bincount(sectors[mask], minlength=8)
             for mask in (original, subset, original & red, subset & red)]
    original_n, subset_n, original_red, subset_red = parts
    draws = np.random.default_rng(1447).integers(0, 8, size=(12000, 8))
    nn, mm, nk, mk = [part[draws].sum(axis=1) for part in parts]
    ok = (nn > 0) & (mm > 0)
    bootstrap = mk[ok] / mm[ok] - nk[ok] / nn[ok]
    return {
        "delta": float(subset_red.sum() / m - original_red.sum() / n),
        "sector_bootstrap95": np.quantile(bootstrap, [.025, .975]).tolist(),
        "max_abs_delta": (n - m) / n,
    }


def compare(objects, weight, mag, red_cut):
    n = objects["object_count"]
    optical = objects["optical_weight"] >= weight
    common = optical & (objects["j_weight"] >= weight)
    red = objects["colour"] >= red_cut
    baseline = optical[:n] & objects["quality"] & (objects["i_mag"] <= mag)
    overlap = common[:n] & baseline
    detected = overlap & objects["j_ok"]
    result = {"minimum_map_weight": weight, "maximum_i_ab": mag, "red_ri_threshold": red_cut,
              "optical_area": float(optical[n:].mean()), "common_area": float(common[n:].mean())}
    for name, mask in zip(SELECTIONS, (baseline, overlap, detected), strict=True):
        result[name] = fraction(mask, red)
    result["footprint_delta"] = paired_difference(baseline, overlap, red, objects["sectors"])
    result["depth_delta"] = paired_difference(overlap, detected, red, objects["sectors"])
    return result


def plot(results, path):
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.0), gridspec_kw={"width_ratios": [1, 1.42]})
    colours = ("#0072B2", "#D55E00", "#009E73")
    glyphs = ("o", "s", "^")
    labels = ("Optical baseline", "Common optical + J footprint", "Common footprint + quality J detection")
    y = np.arange(len(results))
    axes[0].barh(y - .16, [100 * r["primary"]["optical_area"] for r in results],
                 height=.28, color=colours[0], label=labels[0])
    axes[0].barh(y + .16, [100 * r["primary"]["common_area"] for r in results],
                 height=.28, color=colours[1], label=labels[1])
    for j, (side, label) in enumerate(zip(SELECTIONS, labels, strict=True)):
        for i, cluster in enumerate(results):
            result = cluster["primary"][side]
            centre = result["fraction"]
            if centre is None:
                continue
            lo, hi = result["wilson95"]
            yy = i + (j - 1) * .22
            axes[1].errorbar(100 * centre, yy, xerr=[[100 * (centre - lo)], [100 * (hi - centre)]],
                             fmt=glyphs[j], color=colours[j], ms=5.2, lw=1.2, capsize=2.2,
                             label=label if i == 0 else None)
            axes[1].text(62, yy, f'{result["red"]}/{result["count"]}', va="center",
                         ha="left", fontsize=8, color=colours[j], clip_on=False)
    for i, cluster in enumerate(results):
        if cluster["primary"]["common_footprint"]["fraction"] is None:
            axes[1].text(3, i + .22, "No common area", va="center", color="#3a3a3a", fontsize=8)
    axes[0].set_yticks(y, [r["name"].removeprefix("ACT-CL ").replace("-", "−")
                          + f'\n$z={r["redshift"]:.3f}$' for r in results])
    axes[1].set_yticks(y, [])
    axes[0].set(xlabel="Annular area passing the mask (%)", title="a  |  Survey area retained", xlim=(0, 103))
    axes[1].set(xlabel=r"Sources with $r-i\geq0.80$ (%)", title="b  |  Optical-colour tally", xlim=(0, 61))
    axes[1].text(62, -.48, "Red / total", va="bottom", fontsize=8, color=".25")
    for ax in axes:
        ax.set_ylim(len(results) - .58, -.58)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=".89", linewidth=.7)
        ax.set_axisbelow(True)
    handles, names = axes[1].get_legend_handles_labels()
    fig.legend(handles, names, ncol=3, loc="lower center", bbox_to_anchor=(.52, .078),
               frameon=False, fontsize=9)
    fig.suptitle("Euclid coverage and optical colour near four ACT clusters", fontsize=15, weight="semibold", y=.96)
    fig.text(.5, .035, "Measurements in the 1–2 R₅₀₀ annulus · 95% Wilson intervals · Biswajit Jana",
             ha="center", fontsize=9, color=".28")
    fig.subplots_adjust(left=.127, right=.91, bottom=.239, top=.82, wspace=.22)
    fig.savefig(path, dpi=180, bbox_inches="tight", pad_inches=.15)
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=.15,
                metadata={"Title": "Euclid coverage and optical colour near four ACT clusters",
                          "Author": "Biswajit Jana", "CreationDate": None})
    plt.close(fig)


def run(data, output):
    sources = json.loads((ROOT / "inputs.json").read_text())
    previous = COVERAGE_STUDY / "results/effective_pilot.json"
    clusters = [r for r in json.loads(previous.read_text())["clusters"] if r["family"] == "MosaicMasks"]
    paths, hashes = {}, {}
    for tile, inputs in sources.items():
        paths[tile], hashes[tile] = {}, {}
        for band, url in inputs.items():
            paths[tile][band], hashes[tile][band] = get_file(url, data / tile)
    results = []
    for cluster in clusters:
        objects = prepare(cluster, paths[str(cluster["tile_id"])])
        result = {k: cluster[k] for k in ("name", "tile_id", "redshift", "theta500_arcmin")}
        result["all_mer_annulus_sources"] = objects["object_count"]
        result["primary"] = compare(objects, *PRIMARY)
        tests = ((.95, 23, .8), (.8, 22.5, .8), (.8, 23, .65), (.8, 23, .95))
        result["sensitivity"] = [compare(objects, *setting) for setting in tests]
        results.append(result)
    output.mkdir(parents=True, exist_ok=True)
    (output / "colour_results.json").write_text(json.dumps({"input_sha256": hashes, "clusters": results}, indent=2,
                                                         allow_nan=False) + "\n")
    plot(results, output / "colour_coverage.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    run(args.data, args.out)
