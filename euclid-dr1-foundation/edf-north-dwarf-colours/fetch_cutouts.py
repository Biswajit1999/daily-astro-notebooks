"""Read named EDF-N DR1-F mosaics into reproducible, small local cutouts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

from astropy.wcs import WCS
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "euclid-dark-universe"))
from archive import BUCKET, header, window

BANDS = ("VIS", "NIR-Y", "NIR-H")
RADIUS = 180
ARCHIVE_PREFIX = "https://irsacloud.ipac.caltech.edu/ibe/data/euclid"


def pick_products(target, query):
    urls = set(re.findall(r'https://[^<>"\s]+?\.fits', query.read_text()))
    tiles = {}
    for url in urls:
        for band in BANDS:
            if f"_BGSUB-MOSAIC-{band}_" in url:
                tile = url.split("/MER/")[1].split("/")[0]
                tiles.setdefault(tile, {})[band] = url.replace(ARCHIVE_PREFIX, BUCKET)

    candidates = []
    for tile, products in sorted(tiles.items()):
        if set(products) != set(BANDS):
            continue
        info = header(products["VIS"])
        h = info[0]
        if "-DATA_RELEASE_DEEP-" not in h.get("PPLANID", ""):
            continue
        x, y = WCS(h).world_to_pixel_values(target["ra"], target["dec"])
        if not np.isfinite(x+y):
            continue
        margins = [x, h["NAXIS1"]-x, y, h["NAXIS2"]-y]
        if min(margins) > RADIUS+2:
            candidates.append((min(margins), tile, products))
    if not candidates:
        raise ValueError(f"No complete DR1-F deep cutout for {target['object_id']}")
    _, tile, products = max(candidates)
    return tile, products


def fetch_one(target, cache, pinned):
    object_id = target["object_id"]
    if pinned:
        source = pinned[object_id]
        tile = source["tile"]
        products = {band: source["bands"][band]["url"] for band in BANDS}
    else:
        tile, products = pick_products(target, cache / f"{object_id}.xml")
    meta_by_band = {}
    arrays = {}
    for band, url in products.items():
        h, size, meta = header(url)
        if h["NAXIS"] != 2 or h["BITPIX"] != -32 or "-DATA_RELEASE_DEEP-" not in h["PPLANID"]:
            raise ValueError(f"Unexpected format or observing plan in {url}")
        x, y = WCS(h).world_to_pixel_values(target["ra"], target["dec"])
        data, origin, ranges = window((h, size, meta), x, y, RADIUS)
        local = h.copy()
        local["CRPIX1"] -= origin[0]
        local["CRPIX2"] -= origin[1]
        local["NAXIS1"] = data.shape[1]
        local["NAXIS2"] = data.shape[0]
        meta.update(ranges=ranges, origin_xy=list(origin), shape=list(data.shape),
                    magzero=h["MAGZERO"], unit=h["BUNIT"])
        if pinned and meta != source["bands"][band]:
            raise ValueError(f"Archive bytes or metadata changed for {object_id}, {band}")
        meta_by_band[band] = meta
        arrays[band] = data
        arrays[f"{band}_header"] = local.tostring(sep="\n", padding=False)
        print(f"{object_id} tile {tile} {band} {data.shape}", flush=True)
    np.savez_compressed(cache / f"{object_id}.npz", **arrays)
    return object_id, {"tile": tile, "bands": meta_by_band}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=HERE / "image_inputs.json")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    pinned = json.loads(args.manifest.read_text()) if args.manifest.exists() else None
    pairs = json.loads((HERE / "targets.json").read_text())
    targets = [target for pair in pairs for target in pair]
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_one, target, args.cache, pinned) for target in targets]
        result = dict(future.result() for future in futures)
    if not pinned:
        args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
