"""Read central-stamp FWHM metadata from the public MER catalogue PSF FITS."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from astropy.io import fits

from fetch_cutouts import ARCHIVE_PREFIX, BANDS, BUCKET, HERE
from archive import fetch


def image_extension(raw):
    headers = []
    offset = 0
    for _ in range(2):
        end = next(i for i in range(offset, len(raw), 80) if raw[i:i+8] == b"END     ")
        stop = ((end+80+2879)//2880)*2880
        headers.append(fits.Header.fromstring(raw[offset:stop].decode("ascii"), sep=""))
        offset = stop
    if headers[0]["NAXIS"] != 0 or headers[1].get("EXTNAME") != "PSF image":
        raise ValueError("Unexpected catalogue PSF FITS layout")
    return headers[1], offset


def read_model(url):
    raw, _, etag = fetch(url, 0, 28800)
    h, stop = image_extension(raw)
    return {"url": url, "etag": etag, "header_sha256": hashlib.sha256(raw[:stop]).hexdigest(),
            "central_stamp_fwhm_arcsec": h["FWHM"]}


def select_model(query, tile, band):
    urls = set(re.findall(r'https://[^<>"\s]+?\.fits', query.read_text()))
    matches = sorted(url.replace(ARCHIVE_PREFIX, BUCKET) for url in urls
                     if f"/MER/{tile}/" in url and f"_CATALOG-PSF-{band}_" in url)
    if len(matches) != 1:
        raise ValueError(f"Expected one {band} catalogue PSF for tile {tile}, got {len(matches)}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=HERE / "psf_inputs.json")
    args = parser.parse_args()
    images = json.loads((HERE / "image_inputs.json").read_text())
    pinned = json.loads(args.manifest.read_text()) if args.manifest.exists() else None
    jobs = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        for object_id, image in images.items():
            for band in BANDS:
                url = (pinned[object_id][band]["url"] if pinned else
                       select_model(args.cache / f"{object_id}.xml", image["tile"], band))
                jobs[object_id, band] = executor.submit(read_model, url)
        models = {key: {band: jobs[key, band].result() for band in BANDS} for key in images}
    if pinned and models != pinned:
        raise ValueError("Catalogue PSF metadata have changed")
    if not pinned:
        args.manifest.write_text(json.dumps(models, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
