"""Rank held-out EDF-N pairs by reversed optical/infrared filter-peak contrast."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import csv
from functools import lru_cache
from hashlib import file_digest, md5, sha256
import io
import json
from pathlib import Path
from zipfile import ZipFile

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np
from scipy.ndimage import map_coordinates

from archive import get, product, window
from secondary import ECLIPSE

HERE = Path(__file__).resolve().parent
PARENT = HERE/"results"/"holdout_repeaters.csv"
BANDS = ("VIS", "J", "H", "i2")
N_TARGETS = 12
RADIUS = 86
PIXEL = .1


def eclipse_catalogue(cache):
    path = cache/"eclipse.zip"
    if not path.exists():
        path.write_bytes(get(ECLIPSE, 45))
    raw = path.read_bytes()
    if md5(raw).hexdigest() != "56433fecbdc459046ffe9eca44bb4dcf":
        raise ValueError("ECLIPSE catalogue does not match the released archive")
    with ZipFile(io.BytesIO(raw)) as z:
        objects = list(csv.DictReader(io.StringIO(z.read(
            "ECLIPSE_object_catalogue/ECLIPSE_object_catalogue.csv").decode())))
    if len(objects) != 26662:
        raise ValueError("Unexpected ECLIPSE row count")
    return objects, sha256(raw).hexdigest()


def rank(rows, lenses):
    pos = SkyCoord([float(r["ra"]) for r in rows], [float(r["dec"]) for r in rows], unit="deg")
    ls = SkyCoord([float(r["RA_obj"]) for r in lenses], [float(r["DEC_obj"]) for r in lenses], unit="deg")
    neighbours, sep, _ = pos.match_to_catalog_sky(ls)
    passed = []
    for r, index, distance in zip(rows, neighbours, sep.arcsec):
        v1, v2, j1, j2 = [float(r[k]) for k in ("vis_score1", "vis_score2", "j_score1", "j_score2")]
        if float(r["sep_arcsec"]) < .75 or min(v1,v2) < 20 or min(j1,j2) < 12 or float(r["j_dip"]) < .20:
            continue
        # Peak-score ordering within each filter, not calibrated component photometry.
        strength = float(2.5*np.log10((v1/v2)/(j1/j2)))
        if not v1 > v2 or not j2 > j1:
            continue
        entry = {k: (int(v) if k == "tile" else float(v)) for k, v in r.items() if k != "id"}
        passed.append({"candidate":r["id"].replace("EDN-", "NCH-"), **entry,
                       "filtered_peak_contrast_index": strength,
                       "eclipse_match_within_3arcsec": bool(distance <= 3.),
                       "nearest_eclipse_arcsec": float(distance), "nearest_eclipse_id": lenses[index]["Unique_Identifier"]})
    passed.sort(key=lambda r: (-r["filtered_peak_contrast_index"], r["candidate"]))
    return passed, int((sep.arcsec <= 3).sum())


@lru_cache(maxsize=64)
def tile_product(tile, band):
    return product(tile, band)


def registered_window(row, band):
    return register(row, tile_product(row["tile"], band))


def register(row, p):
    h, _, meta = p
    w = WCS(h).celestial
    x, y = w.world_to_pixel_values(row["ra"], row["dec"])
    raw, origin, ranges = window(p, x, y, RADIUS)
    tangent = WCS(naxis=2)
    tangent.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    tangent.wcs.crval = [row["ra"], row["dec"]]
    tangent.wcs.crpix = [RADIUS-9., RADIUS-9.]
    tangent.wcs.cdelt = [-PIXEL/3600, PIXEL/3600]
    tangent.wcs.radesys = "ICRS"
    yy, xx = np.indices((2*(RADIUS-10)+1,)*2, dtype=float)
    wx, wy = w.world_to_pixel_values(*tangent.pixel_to_world_values(xx, yy))
    grid = map_coordinates(raw, [wy-origin[1], wx-origin[0]], order=1, cval=np.nan)
    return grid, dict(meta, origin_xy=list(origin), ranges=ranges, finite_fraction=float(np.isfinite(grid).mean()))


def fetch_one(target, cache):
    name = target["candidate"]
    path = cache/f"{name}.npz"
    if path.exists():
        with np.load(path) as old:
            return name, json.loads(str(old["metadata"]))
    images, details = {}, {}
    for band in BANDS:
        try:
            images[band], details[band] = registered_window(target, band)
        except Exception as exc:
            details[band] = {"error": str(exc)[:650]}
    if images:
        np.savez_compressed(path, **images, metadata=json.dumps(details))
    print(name, [band for band in BANDS if band in images], flush=True)
    return name, details


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cache = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    with PARENT.open() as f:
        rows = list(csv.DictReader(f))
    lenses, lens_hash = eclipse_catalogue(cache)
    ranked, lens_matches = rank(rows, lenses)
    with PARENT.open("rb") as f:
        parent_hash = file_digest(f, "sha256").hexdigest()
    chosen = [r for r in ranked if not r["eclipse_match_within_3arcsec"]][:N_TARGETS]
    result = {"parent_count": len(rows), "parent_sha256": parent_hash,
              "eclipse_rows": len(lenses), "eclipse_sha256": lens_hash, "parent_with_eclipse_within_3arcsec": lens_matches,
              "n_brightness_and_inversion_pass": len(ranked), "candidates": chosen}
    path = args.output or cache/"selection.json"
    path.write_text(json.dumps(result, indent=2)+"\n")
    with ThreadPoolExecutor(max_workers=7) as pool:
        result["mosaics"] = dict(pool.map(lambda target: fetch_one(target, cache), chosen))
    path.write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
