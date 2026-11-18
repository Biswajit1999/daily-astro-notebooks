"""Fetch checked WCS cutouts in the DES J0330-5228 field."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import argparse
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


def cutout(band,key,inputs):
    h,offset,info=header(f"{BUCKET}/{key}")
    w=WCS(h).celestial
    x,y=w.world_to_pixel(SkyCoord(*CENTRE,unit="deg"))
    data,(x0,y0),rows=window((h,offset,info),x,y,245)
    w.wcs.crpix -= [x0,y0]
    out=w.to_header()
    for column in ("BUNIT","MAGZERO","FILTER","PPLANID"):
        if column in h:
            out[column]=h[column]
    fits.writeto(inputs/f"arc_{band}.fits",data,out,overwrite=True)
    return {"band":band,**info,"tile":TILE,"ranges":rows,"origin_native_xy":[x0,y0]}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path)
    args=p.parse_args()
    keys=products(args.inputs)
    with ThreadPoolExecutor(4) as pool:
        results=list(pool.map(lambda band:cutout(band,keys[band],args.inputs), BANDS))
    (args.inputs/"arc_image_manifest.json").write_text(json.dumps(results,indent=2)+"\n")
