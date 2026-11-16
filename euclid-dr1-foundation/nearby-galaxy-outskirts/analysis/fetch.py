"""Fetch small, checksum-recorded sections of public Euclid DR1-F MER mosaics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

BASE = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com/"
HALF = 1200
BANDS = {"vis": ("VIS", "BGSUB-MOSAIC-VIS_"),
         "vis_sky": ("VIS", "BGMOD-VIS_"),
         "h": ("NISP", "BGSUB-MOSAIC-NIR-H_"),
         "vis_rms": ("VIS", "MOSAIC-VIS-RMS_")}


def range_bytes(key, start, stop):
    hdr = {"Range": f"bytes={start}-{stop-1}"}
    with urlopen(Request(BASE+key, headers=hdr), timeout=80) as reply:
        if reply.status != 206 or not reply.headers.get("Content-Range", "").startswith(f"bytes {start}-{stop-1}/"):
            raise OSError(f"Unexpected Range response for {key}")
        data = reply.read(stop-start+1)
    if len(data) != stop-start:
        raise OSError(f"Incomplete byte range for {key}")
    return data


def list_keys(tile, instrument):
    prefix = f"dr1/MER/{tile}/{instrument}/"
    with urlopen(BASE+"?"+urlencode({"list-type":2,"prefix":prefix}),timeout=45) as response:
        root = ET.fromstring(response.read())
    return sorted(node.findtext("{*}Key") for node in root.findall("{*}Contents"))


def extract(key, ra, dec, output, *, half_size=HALF, stripe_rows=256):
    raw = range_bytes(key, 0, 28800)
    end = next(i+80 for i in range(0,len(raw),80) if raw[i:i+8]==b"END     ")
    hdr = fits.Header.fromstring(raw[:end].decode("ascii"),sep="")
    if hdr["NAXIS"]!=2 or hdr["BITPIX"]!=-32 or hdr.get("BSCALE",1)!=1 or hdr.get("BZERO",0)!=0:
        raise ValueError(f"Unsupported primary image layout for {key}")
    nx,ny=hdr["NAXIS1"],hdr["NAXIS2"]
    wcs=WCS(hdr).celestial
    x,y=(round(float(n)) for n in wcs.world_to_pixel_values(ra,dec))
    left,right=max(0,x-half_size),min(nx,x+half_size)
    low,high=max(0,y-half_size),min(ny,y+half_size)
    if left>=right or low>=high:
        raise ValueError(f"Position lies outside {key}")
    # Read a stripe of native rows per request, then retain the selected columns.
    data=np.full((high-low,right-left),np.nan,dtype=">f4")
    offset=((end+2879)//2880)*2880
    for bottom in range(low,high,stripe_rows):
        top=min(bottom+stripe_rows,high)
        stripe=range_bytes(key,offset+bottom*nx*4,offset+top*nx*4)
        data[bottom-low:top-low]=np.frombuffer(stripe,">f4").reshape(-1,nx)[:,left:right]
    header=wcs.slice(np.s_[low:high,left:right]).to_header()
    for k in ("BUNIT","MAGZERO","FILTER"):
        if k in hdr:
            header[k]=hdr[k]
    fits.writeto(output,data,header,overwrite=True)
    return {"key":key,"bounds":[left,right,low,high],"pixel_sha256":hashlib.sha256(data.tobytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--bands",nargs="+",choices=BANDS,default=["vis"])
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with args.targets.open() as stream:
        targets=list(csv.DictReader(stream))
    jobs=[(t,b) for t in targets for b in args.bands]
    def run(job):
        t,band=job
        name=t["object"]
        record={"target":name,"band":band}
        try:
            instrument,pattern=BANDS[band]
            keys=[k for k in list_keys(t["tile"],instrument) if pattern in k and k.endswith(".fits")]
            if len(keys)!=1:
                raise ValueError(f"{len(keys)} products match {pattern}")
            record.update(extract(keys[0],float(t["ra"]),float(t["dec"]),args.output/f"{name}_{band}.fits"))
        except (OSError,ValueError,StopIteration) as exc:
            record["error"]=str(exc)
        print(record,flush=True)
        return record
    with ThreadPoolExecutor(8) as pool:
        records=list(pool.map(run,jobs))
    (args.output/("cutouts_"+"_".join(args.bands)+".json")).write_text(json.dumps(records,indent=2)+"\n")


if __name__=="__main__":
    main()
