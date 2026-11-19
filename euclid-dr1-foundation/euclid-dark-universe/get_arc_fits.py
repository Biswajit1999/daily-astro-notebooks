"""Fetch checked WCS cutouts in the DES J0330-5228 field."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import argparse
import hashlib
import json

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS

from archive import BUCKET, header, window

CENTRE = (52.737216, -52.470283)
TILE = "102017310"
BANDS = ["VIS","NIR-H","DES-G","DES-I"]
SIA = "https://irsa.ipac.caltech.edu/SIA"


def products(inputs):
    p=inputs/"sia1.xml"
    if not p.exists():
        args=urlencode({"POS":f"CIRCLE {CENTRE[0]} {CENTRE[1]} 0.01",
                        "COLLECTION":"euclid_dr1_wide_DpdMerBksMosaic","MAXREC":"60"})
        with urlopen(f"{SIA}?{args}",timeout=60) as f:
            p.write_bytes(f.read())
    table=Table.read(p,format="votable")
    keys={}
    for row in table:
        for value in row:
            url=str(value)
            if ("https://irsacloud.ipac.caltech.edu/ibe/data/euclid/dr1/" not in url
                    or f"/{TILE}/" not in url or "_BGSUB-MOSAIC-" not in url):
                continue
            band=url.split("_BGSUB-MOSAIC-")[1].split("_")[0]
            if band in BANDS:
                keys[band]="dr1/"+url.split("/euclid/dr1/")[1]
    if set(keys)!=set(BANDS):
        raise ValueError(f"Missing products for {TILE}: {list(keys)}")
    return keys


def cutout(band,key,inputs,expected=None):
    h,offset,info=header(f"{BUCKET}/{key}")
    w=WCS(h).celestial
    x,y=w.world_to_pixel(SkyCoord(*CENTRE,unit="deg"))
    data,(x0,y0),rows=window((h,offset,info),x,y,245)
    w.wcs.crpix -= [x0,y0]
    out=w.to_header()
    for column in ("BUNIT","MAGZERO","FILTER","PPLANID"):
        if column in h:
            out[column]=h[column]
    record = {"band":band,**info,"tile":TILE,"ranges":rows,"origin_native_xy":[x0,y0]}
    if expected:
        for field in ("etag", "bytes", "header_sha256", "ranges", "origin_native_xy"):
            if record[field] != expected[field]:
                raise ValueError(f"{band} differs from the pinned manifest in {field}.")
    fits.writeto(inputs/f"arc_{band}.fits",data,out,overwrite=True)
    return record


def replay_products(manifest):
    records = json.loads(manifest.read_text())
    by_band = {row["band"]: row for row in records}
    if len(records) != len(BANDS) or set(by_band) != set(BANDS):
        raise ValueError("The manifest must identify exactly one released mosaic per band.")
    prefix = f"{BUCKET}/dr1/MER/{TILE}/"
    if any(row["tile"] != TILE or not row["url"].startswith(prefix)
           or f"_BGSUB-MOSAIC-{band}_" not in row["url"]
           for band, row in by_band.items()):
        raise ValueError("The manifest does not match the released DES J0330-5228 mosaic set.")
    return by_band


def retrieve(inputs, manifest=None):
    inputs.mkdir(parents=True, exist_ok=True)
    expected = replay_products(manifest) if manifest else {}
    keys = ({band: row["url"].removeprefix(f"{BUCKET}/") for band, row in expected.items()}
            if expected else products(inputs))
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda band: cutout(band, keys[band], inputs, expected.get(band)), BANDS))
    hashes = {}
    for band in BANDS:
        path = inputs / f"arc_{band}.fits"
        with path.open("rb") as stream:
            hashes[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    (inputs / "fits_sha256.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    (inputs / "arc_image_manifest.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path)
    p.add_argument("--discover", action="store_true", help="Query the live SIA service instead of replaying the archived mosaic manifest.")
    args=p.parse_args()
    manifest = Path(__file__).resolve().parent / "inputs/arc_image_manifest.json"
    retrieve(args.inputs, manifest=None if args.discover else manifest)
