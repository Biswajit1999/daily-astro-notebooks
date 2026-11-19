"""Compare geometric and effective coverage inside a pilot set of released tiles."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import shutil
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy_healpix import HEALPix
from mocpy import MOC
import numpy as np

from analyze import angular_grid, download_inputs, samples

BUCKET = "https://nasa-irsa-euclid-dr1.s3.us-east-1.amazonaws.com/"
PREFIX = "dr1/VMPZ_EFFECTIVE_COVERAGE/DpdHealpixEffectiveCoverageVMPZ/"
TILE_LIMIT = 64
FAMILIES = ("EffCovOnly", "MosaicMasks")


CASE_NAME = "ACT-CL J0436.5-4450"
CASE_TILE = 102024504
CASE_BAND_FILES = {
    "DECAM_g": "155942.034033",
    "DECAM_i": "160134.246414",
    "VIS": "160354.476505",
    "NIR_J": "160546.034996",
    "NIR_Y": "160729.302550",
    "DECAM_r": "160921.989621",
    "DECAM_z": "161108.451769",
}


def first_catalogue_masks():
    """Take the first 64 CL FITS keys per processing family in bucket order."""
    urls = []
    for family in FAMILIES:
        opts = {"list-type": "2", "prefix": PREFIX + f"LE3_VMPZ-ID-{family}_",
                "max-keys": "500"}
        with urlopen(BUCKET + "?" + urlencode(opts), timeout=40) as response:
            listing = ET.parse(response)
        keys = [row.text for row in listing.findall(".//{*}Contents/{*}Key")
                if "HPEFFECTIVECOVERAGE-CL_" in row.text and row.text.endswith(".fits")]
        if len(keys) < TILE_LIMIT:
            raise ValueError(f"Unexpected file listing for {family}")
        urls.extend({"url": BUCKET + key, "family": family} for key in keys[:TILE_LIMIT])
    return urls


def fetch_fits(url, data):
    local = data / url.rsplit("/", 1)[-1]
    if not local.exists():
        part = local.with_suffix(".part")
        with urlopen(url, timeout=60) as response, part.open("wb") as output:
            shutil.copyfileobj(response, output)
        part.replace(local)
    return local


def get_masks(data, manifest_path):
    data.mkdir(parents=True, exist_ok=True)
    urls = (json.loads(manifest_path.read_text()) if manifest_path.exists()
            else first_catalogue_masks())

    def fetch(entry):
        url = entry["url"]
        local = fetch_fits(url, data)
        digest = sha256(local.read_bytes()).hexdigest()
        if "sha256" in entry and entry["sha256"] != digest:
            raise ValueError(f"Changed input {local}")
        tile_id = fits.getval(local, "TILEID", ext=0)
        return dict(url=url, family=entry["family"], sha256=digest, tile_id=tile_id), local

    with ThreadPoolExecutor(max_workers=10) as pool:
        files = list(pool.map(fetch, urls))
    manifest_path.write_text(json.dumps([entry for entry, _ in files], indent=2) + "\n")
    return files


def inspect_bands(cluster, data, grid, draws):
    data.mkdir(parents=True, exist_ok=True)
    lon, lat = angular_grid(np.radians([cluster["ra_deg"]]),
                            np.radians([cluster["dec_deg"]]),
                            np.array([cluster["theta500_arcmin"]]), (1, 2), draws)
    cells = grid.lonlat_to_healpix(lon.ravel(), lat.ravel())
    base_url = BUCKET + f"dr1/VMPZ_HEALPIX_COVERAGE_MASK/{CASE_TILE}/"
    results = {}
    for band, tag in CASE_BAND_FILES.items():
        url = base_url + f"EUC_LE3_VMPZ-ID_HPCOVERAGE-{CASE_TILE}_20250803T{tag}Z_0.12.fits"
        local = fetch_fits(url, data)
        with fits.open(local) as fits_file:
            header = fits_file[0].header
            assert header["TILEID"] == CASE_TILE and header["FILTER"] == band
            mask = fits_file["COVERAGE_MASK"]
            assert mask.header["NSIDE"] == grid.nside and mask.header["ORDERING"] == "NESTED"
            weights = dict(zip(mask.data["PIXEL"], mask.data["WEIGHT"], strict=True))
        values = np.array([weights[cell] for cell in cells], dtype=float)
        results[band] = {
            "mean_weight": float(values.mean()),
            "fraction_positive": float((values > 0).mean()),
            "url": url,
            "sha256": sha256(local.read_bytes()).hexdigest(),
        }
    return results


def evaluate(data, output):
    download_inputs(data)
    output.mkdir(parents=True, exist_ok=True)
    files = get_masks(data / "effective", output / "effective_inputs.json")
    table = Table.read(data / "act_dr6_v1.fits")
    mocs = {name: MOC.from_fits(data / f"{name}.fits")
            for name in ("euclid_wide", "mer_wide_survey")}
    all_centres = SkyCoord(table["RADeg"], table["decDeg"], unit="deg")
    draws = samples(15, 663)
    sectors = np.floor(draws[:, 1] * 8).astype(int)
    n_sector = np.bincount(sectors, minlength=8)
    grid = HEALPix(nside=16384, order="nested")
    complete = {}
    for entry, local in files:
        with fits.open(local) as hdu:
            mask = hdu["EFFECTIVE_COVERAGE_MASK"]
            assert mask.header["NSIDE"] == 16384 and mask.header["ORDERING"] == "NESTED"
            assert hdu[0].header["METHOD"] == "CL"
            order = np.argsort(mask.data["PIXEL"])
            pixels = np.asarray(mask.data["PIXEL"][order], dtype=np.int64)
            weights = np.asarray(mask.data["WEIGHT"][order], dtype=float)
        assert len(pixels) and (np.diff(pixels) > 0).all()
        assert np.isfinite(weights).all() and weights.min() >= 0 and weights.max() <= 1.000001
        mid = SkyCoord(*grid.healpix_to_lonlat(pixels[len(pixels) // 2]))
        # A conservative bounding cap keeps the HEALPix lookups small.
        tile_points = SkyCoord(*grid.healpix_to_lonlat(pixels))
        tile_radius = mid.separation(tile_points).max() + 0.01 * u.deg
        nearby = np.flatnonzero(mid.separation(all_centres) <= tile_radius)

        for index in nearby:
            centre, row = all_centres[index], table[index]
            key = (entry["family"], str(row["name"]))
            if key in complete:
                continue
            centre_cell = int(grid.lonlat_to_healpix(centre.ra, centre.dec))
            if not np.isin(centre_cell, pixels):
                continue
            rad = np.array([row["theta500Arcmin"]])
            lon, lat = angular_grid(np.array([centre.ra.rad]), np.array([centre.dec.rad]),
                                    rad, (1, 2), draws)
            cells = grid.lonlat_to_healpix(lon.ravel(), lat.ravel())
            idx = np.minimum(np.searchsorted(pixels, cells), len(pixels) - 1)
            if not np.array_equal(pixels[idx], cells):
                continue
            values = weights[idx].clip(0, 1)
            geometry = {name: float(mask.contains_lonlat(lon.ravel(), lat.ravel()).mean())
                        for name, mask in mocs.items()}
            octants = np.bincount(sectors, weights=values, minlength=8) / n_sector
            complete[key] = {
                "name": str(row["name"]),
                "family": entry["family"],
                "tile_id": entry["tile_id"],
                "ra_deg": float(centre.ra.deg),
                "dec_deg": float(centre.dec.deg),
                "redshift": float(row["redshift"]),
                "theta500_arcmin": float(rad[0]),
                "wide_tile_fraction": geometry["euclid_wide"],
                "mer_geometric_fraction": geometry["mer_wide_survey"],
                "effective_fraction": float(values.mean()),
                "effective_min_octant": float(octants.min()),
            }
    report = {
        "tiles_by_family": {
            family: len({entry["tile_id"] for entry, _ in files if entry["family"] == family})
            for family in FAMILIES
        },
        "unique_tiles": len({entry["tile_id"] for entry, _ in files}),
        "clusters": [complete[key] for key in sorted(complete)],
    }
    case = complete[("MosaicMasks", CASE_NAME)]
    assert case["tile_id"] == CASE_TILE
    report["case_band_check"] = {"name": CASE_NAME, "tile_id": CASE_TILE,
                                 "bands": inspect_bands(case, data / str(CASE_TILE), grid, draws)}
    (output / "effective_pilot.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    evaluate(args.data, args.out)
