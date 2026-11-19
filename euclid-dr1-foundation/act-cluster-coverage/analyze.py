"""Measure Euclid DR1-Foundation footprint coverage around ACT DR6 clusters."""

import argparse
import csv
from gzip import GzipFile
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
import matplotlib
import numpy as np
from matplotlib.patches import Circle
from mocpy import MOC
from scipy.stats import qmc

matplotlib.use("Agg")
import matplotlib.pyplot as plt

S3 = "https://nasa-irsa-euclid-dr1.s3.us-east-1.amazonaws.com/dr1/MOC/"
SOURCES = {
    "act_dr6_v1.fits": (
        "https://lambda.gsfc.nasa.gov/data/suborbital/ACT/actadv_dr6_cluster_cat/"
        "DR6_cluster-catalog_v1.0.fits"
    ),
    "euclid_wide.fits": S3 + "euclid_dr1_wide.moc.moc.fits",
    "mer_wide_survey.fits": S3 + "euclid_dr1_mer_catalogue_wide_survey.moc.fits",
}
RADIAL_BINS = {
    "core": (0, 0.5),
    "inner": (0.5, 1),
    "outskirts": (1, 2),
    "background": (2, 3),
}
CUTS = (0.90, 0.95, 0.99)


def download_inputs(path):
    path.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for name, url in SOURCES.items():
        target = path / name
        if not target.exists():
            partial = target.with_suffix(".part")
            with urlopen(url, timeout=60) as response, partial.open("wb") as output:
                shutil.copyfileobj(response, output)
            partial.replace(target)
        inputs[name] = {"url": url, "sha256": sha256(target.read_bytes()).hexdigest()}
    return inputs


def angular_grid(ra, dec, radius_arcmin, bin_edges, draws):
    """Uniform solid-angle positions in an annulus, with PA east of north."""
    scale = np.radians(radius_arcmin[:, None] / 60)
    lo, hi = bin_edges
    low = np.sin(scale * lo / 2) ** 2
    high = np.sin(scale * hi / 2) ** 2
    distance = 2 * np.arcsin(np.sqrt(low + (high - low) * draws[:, 0]))
    angle = draws[:, 1] * (2 * np.pi)
    sinlat, coslat = np.sin(dec[:, None]), np.cos(dec[:, None])
    lon0 = ra[:, None]
    cos_d = np.cos(distance)
    sin_d = np.sin(distance)
    # Rotate the local east, north, and radial unit vectors into ICRS.
    outward = coslat * cos_d - sinlat * sin_d * np.cos(angle)
    east = sin_d * np.sin(angle)
    north = sinlat * cos_d + coslat * sin_d * np.cos(angle)
    lon = (lon0 + np.arctan2(east, outward)) % (2 * np.pi)
    lat = np.arctan2(north, np.hypot(outward, east))
    return lon * u.rad, lat * u.rad


def measure(masks, ra, dec, radius, bin_edges, draws):
    """Return coverage by footprint and position-angle octant."""
    sectors = np.floor(draws[:, 1] * 8).astype(int)
    membership = (sectors[:, None] == np.arange(8)).astype(np.float32)
    denominator = membership.sum(axis=0)
    result = np.empty((len(masks), len(ra), 8), dtype=float)
    batch_size = min(128, max(1, 524288 // len(draws)))
    for start in range(0, len(ra), batch_size):
        batch = slice(start, start + batch_size)
        lon, lat = angular_grid(ra[batch], dec[batch], radius[batch], bin_edges, draws)
        for index, mask in enumerate(masks):
            weights = mask.contains_lonlat(lon, lat).astype(np.float32)
            result[index, batch] = (weights @ membership) / denominator
    return result


def samples(power, seed):
    return qmc.Sobol(2, scramble=True, rng=np.random.default_rng(seed)).random_base2(power)


def summary(centres, covered, refined, valid, legacy, radius_low, radius_high,
            optical, has_optical):
    result = {}
    n_in = centres & valid
    for label, subset in (("all", valid), ("act_legacy", valid & legacy)):
        inside = n_in & subset
        centre_count = int(inside.sum())
        ring_summary = {}
        for name, fractions in covered.items():
            means = fractions.mean(axis=1)
            ring_summary[name] = {
                "below_cut": {str(cut): int((inside & (means < cut)).sum()) for cut in CUTS},
                "below_cut_any_octant": {
                    str(cut): int((inside & (fractions.min(axis=1) < cut)).sum())
                    for cut in CUTS
                },
                "outside_centre_meeting_90pct": int((subset & ~centres & (means >= .90)).sum()),
            }
        mean = covered["outskirts"].mean(axis=1)
        size_changes = (radius_low.mean(axis=1) >= .90) != (radius_high.mean(axis=1) >= .90)
        opt_changes = (optical.mean(axis=1) >= .90) != (mean >= .90)
        total90 = inside & (mean >= .90)
        result[label] = {
            "catalogue_entries": int(subset.sum()),
            "centres_inside": centre_count,
            "rings": ring_summary,
            "outskirts_90pct_total_with_octant_below_50pct": int(
                (total90 & (covered["outskirts"].min(axis=1) < .50)).sum()
            ),
            "outskirts_90pct_fraction_switch_radius_minus_to_plus_1sigma": int(
                (inside & size_changes).sum()
            ),
            "outskirts_90pct_fraction_switch_sz_to_optical_centre": int(
                (inside & has_optical & opt_changes).sum()
            ),
            "inside_with_optical_centres": int((inside & has_optical).sum()),
            "outskirts_sampling_abs_delta_max": float(refined[inside].max(initial=0)),
        }
    return result


def write_rows(path, table, sets):
    fields = ["name", "ra_deg", "dec_deg", "redshift", "redshift_type",
              "theta500_arcmin", "theta500_err_arcmin", "fixed_snr", "act_legacy"]
    for footprint in sets:
        fields += [f"{footprint}_centre_inside"]
        for ring in RADIAL_BINS:
            fields += [f"{footprint}_{ring}_fraction", f"{footprint}_{ring}_min_octant"]
        fields += [
            f"{footprint}_outskirts_quad", f"{footprint}_outskirts_sample_delta",
            f"{footprint}_outskirts_fraction_radius_minus_1sigma",
            f"{footprint}_outskirts_fraction_radius_plus_1sigma",
            f"{footprint}_outskirts_fraction_optical_centre",
        ]
        fields += [f"{footprint}_outskirts_octant_{i}" for i in range(8)]
    use = np.logical_or.reduce([
        record["centres"] | (record["rings"]["background"].max(axis=1) > 0)
        | (record["rings"]["outskirts"].max(axis=1) > 0)
        | (record["rings"]["inner"].max(axis=1) > 0)
        | (record["rings"]["core"].max(axis=1) > 0)
        for record in sets.values()
    ])
    octant_pa = (np.arange(8) + .5) * (2 * np.pi / 8)
    with path.open("wb") as target, GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as compressed:
        return write_table(compressed, fields, octant_pa, use, table, sets)


def write_table(compressed, fields, octant_pa, use, table, sets):
    with TextIOWrapper(compressed, newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for i in np.flatnonzero(use):
            row = table[i]
            values = [
                str(row["name"]).strip(), f"{row['RADeg']:.8f}", f"{row['decDeg']:.8f}",
                f"{row['redshift']:.6f}", str(row["redshiftType"]).strip(),
                f"{row['theta500Arcmin']:.6f}", f"{row['theta500Arcmin_err']:.6f}",
                f"{row['fixed_SNR']:.4f}", int(row["legacy"]),
            ]
            for record in sets.values():
                values.append(int(record["centres"][i]))
                for ring in RADIAL_BINS:
                    octants = record["rings"][ring][i]
                    values.extend([f"{octants.mean():.6f}", f"{octants.min():.6f}"])
                octants = record["rings"]["outskirts"][i]
                quadrupole = abs(octants @ np.exp(2j * octant_pa)) / octants.sum() if octants.sum() else np.nan
                values.extend([f"{quadrupole:.6f}", f"{record['sample_delta'][i]:.6f}"])
                for key in ("radius_low", "radius_high", "optical"):
                    value = record[key][i].mean()
                    values.append(f"{value:.6f}" if np.isfinite(value) else "")
                values.extend(f"{value:.6f}" for value in octants)
            writer.writerow(values)
    return int(use.sum())


def plot(path, collection, details, table, mer_moc):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.65), layout="constrained",
                             gridspec_kw={"width_ratios": [1.05, 1.0, 1.13]})
    colors = ["#2d2d2d", "#878787"]
    labels = ["Wide-tile footprint", "MER Wide Survey footprint"]
    x = np.arange(len(RADIAL_BINS))
    for i, (key, record) in enumerate(collection.items()):
        counts = details[key]["all"]
        n = counts["centres_inside"]
        y = np.array([counts["rings"][b]["below_cut"]["0.9"] for b in RADIAL_BINS])
        axes[0].bar(x + (i - .5) * .35, 100 * y / n, width=.30, color=colors[i],
                    label=f"{labels[i]} (n={n:,})")
        mean = record["rings"]["outskirts"].mean(axis=1)
        octant_min = record["rings"]["outskirts"].min(axis=1)
        keep = record["centres"] & ((mean < 1) | (octant_min < 1))
        axes[1].scatter(mean[keep] * 100, octant_min[keep] * 100, s=10, alpha=.54,
                        color=colors[i], linewidths=0, label=labels[i])
    axes[0].set_xticks(x, ["0–0.5", "0.5–1", "1–2", "2–3"])
    axes[0].set(xlabel=r"Annulus limits ($R/R_{500}$)", ylabel="Centres inside with <90% area (%)")
    axes[0].legend(fontsize=8, frameon=False, loc="upper left")
    axes[1].set(xlabel=r"$1$–$2,R_{500}$ annulus area covered (%)",
                ylabel="Least-covered 45° sector (%)", xlim=(-2, 102), ylim=(-2, 102))
    axes[1].axvline(90, ls="--", c=".55", lw=.8)
    axes[1].axhline(50, ls=":", c=".55", lw=.8)
    example = collection["mer_wide_survey"]
    its_ring = example["rings"]["outskirts"]
    candidate = example["centres"] & (its_ring.mean(axis=1) >= .9)
    if candidate.any():
        index = np.argmin(np.where(candidate, its_ring.min(axis=1), 1.1))
        draw_example(axes[2], table[index], mer_moc, its_ring[index])
    for ax in axes[:2]:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.22)
        ax.set_axisbelow(True)
    fig.suptitle("Euclid DR1-Foundation coverage around ACT DR6 clusters", fontsize=15,
                 fontweight="semibold")
    fig.supxlabel("Biswajit Jana  ·  ACT DR6 v1.0 (NASA LAMBDA)  ·  Euclid DR1-Foundation (ESA and IRSA)",
                  fontsize=9, color=".28")
    fig.savefig(path, dpi=190)


def draw_example(ax, row, mask, octants):
    centre = SkyCoord(row["RADeg"], row["decDeg"], unit="deg")
    theta = float(row["theta500Arcmin"])
    half = 2.35 * theta
    edge = np.linspace(-half, half, 321)
    pixel_centres = (edge[1:] + edge[:-1]) * .5
    east, north = np.meshgrid(pixel_centres, pixel_centres)
    rho = np.hypot(east, north)
    pa = np.arctan2(east, north)
    positions = centre.directional_offset_by(pa * u.rad, rho * u.arcmin)
    covered = mask.contains_skycoords(positions)
    ax.imshow(covered, origin="lower", cmap="gray_r", vmin=0, vmax=2.5,
              interpolation="nearest", extent=(-half, half, -half, half))
    for scale in (1, 2):
        ax.add_patch(Circle((0, 0), scale * theta, fill=False, edgecolor=".25", lw=.8))
    for j in range(8):
        direction = 2 * np.pi * j / 8
        ax.plot([theta * np.sin(direction), 2 * theta * np.sin(direction)],
                [theta * np.cos(direction), 2 * theta * np.cos(direction)],
                c=".35", lw=.55, ls="--")
    ax.plot(0, 0, "k+", ms=7)
    j = int(octants.argmin())
    direction = 2 * np.pi * (j + .5) / 8
    ax.plot(1.5 * theta * np.sin(direction), 1.5 * theta * np.cos(direction),
            "o", mfc="white", mec="black", ms=4)
    ax.set(xlim=(half, -half), ylim=(-half, half), xlabel="East offset (arcmin)",
           ylabel="North offset (arcmin)")
    ax.set_title(f"{row['name']}\n{100 * octants.mean():.1f}% covered · worst sector {100 * octants.min():.1f}%",
                 fontsize=9.5)


def run(data, output):
    inputs = download_inputs(data)
    table = Table.read(data / "act_dr6_v1.fits")
    rad = np.asarray(table["theta500Arcmin"], dtype=float)
    rad_error = np.asarray(table["theta500Arcmin_err"], dtype=float)
    valid = np.isfinite(rad) & (rad > 0) & (3 * rad < 180 * 60)
    assert valid.all(), "Check the catalogue for invalid angular radii"
    legacy = ((table["fixed_SNR"] > 5.5) & (table["flags"] == 0) & table["footprint_Legacy"])
    table["legacy"] = legacy
    ra, dec = [np.radians(np.asarray(table[key])) for key in ("RADeg", "decDeg")]
    opt_ra, opt_dec = [np.radians(np.asarray(table[key])) for key in ("opt_RADeg", "opt_decDeg")]
    # The v1.0 FITS uses -99 degrees for missing optical coordinates.
    has_opt = ((opt_ra >= 0) & (opt_ra < 2 * np.pi) & (np.abs(opt_dec) <= np.pi / 2)
               & ((opt_ra != 0) | (opt_dec != 0)))

    keys = ("wide_tile", "mer_wide_survey")
    masks = [MOC.from_fits(data / name) for name in ("euclid_wide.fits", "mer_wide_survey.fits")]
    inside = np.array([mask.contains_lonlat(ra * u.rad, dec * u.rad) for mask in masks])
    coarse, fine = samples(12, 4158), samples(15, 663)
    rings = {}
    for ring, bounds in RADIAL_BINS.items():
        f = measure(masks, ra, dec, rad, bounds, coarse)
        intersects = f.min(axis=(0, 2)) < 1
        intersects &= (f.max(axis=(0, 2)) > 0) | inside.any(axis=0)
        if ring == "outskirts":
            sample_delta = np.zeros_like(inside, dtype=float)
            coarse_means = f[:, intersects].mean(axis=2)
        f[:, intersects] = measure(masks, ra[intersects], dec[intersects], rad[intersects], bounds, fine)
        if ring == "outskirts":
            sample_delta[:, intersects] = np.abs(f[:, intersects].mean(axis=2) - coarse_means)
        rings[ring] = f

    # Sensitivity checks concern only the centre-selected samples.
    subset = inside.any(axis=0)
    bounds = RADIAL_BINS["outskirts"]
    alt = {}
    for label, x, y, radius, use in (
        ("radius_low", ra, dec, rad - rad_error, subset),
        ("radius_high", ra, dec, rad + rad_error, subset),
        ("optical", opt_ra, opt_dec, rad, subset & has_opt),
    ):
        use = use & np.isfinite(radius) & (radius > 0)
        values = np.full((len(masks), len(table), 8), np.nan)
        values[:, use] = measure(masks, x[use], y[use], radius[use], bounds, coarse)
        partial = use & ((values.min(axis=2) < 1) & (values.max(axis=2) > 0)).any(axis=0)
        values[:, partial] = measure(masks, x[partial], y[partial], radius[partial], bounds, fine)
        alt[label] = values

    results = {"inputs": inputs, "radial_bins_r500": RADIAL_BINS, "footprints": {}}
    sets = {}
    for i, key in enumerate(keys):
        ring = {name: val[i] for name, val in rings.items()}
        record = {name: val[i] for name, val in alt.items()}
        sets[key] = dict(centres=inside[i], rings=ring, sample_delta=sample_delta[i], **record)
        stats = summary(inside[i], ring, sample_delta[i], valid, legacy,
                        record["radius_low"], record["radius_high"], record["optical"], has_opt)
        stats["area_sq_deg"] = float(masks[i].sky_fraction * 4 * np.pi * (180 / np.pi) ** 2)
        stats["moc_order"] = int(masks[i].max_order)
        results["footprints"][key] = stats

    results["centre_cross_tabulation"] = {
        "both": int((inside[0] & inside[1]).sum()),
        "wide_tile_only": int((inside[0] & ~inside[1]).sum()),
        "mer_wide_survey_only": int((~inside[0] & inside[1]).sum()),
        "neither": int((~inside[0] & ~inside[1]).sum()),
    }
    output.mkdir(parents=True, exist_ok=True)
    results["output_rows"] = write_rows(output / "clusters.csv.gz", table, sets)
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    plot(output / "coverage.png", sets, results["footprints"], table, masks[1])
    print(json.dumps({key: value["all"] for key, value in results["footprints"].items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    run(args.data, args.out)
