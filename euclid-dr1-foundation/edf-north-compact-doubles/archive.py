"""Read checked byte ranges of public Euclid DR1-F MER FITS products."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.client import IncompleteRead
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import time
import xml.etree.ElementTree as ET

from astropy.io import fits
import numpy as np

BUCKET = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com"
TILES = tuple(range(101829775, 101829781))
WIDTH = 6144


def get(url, seconds=25):
    return subprocess.run(["curl", "-fsSL", "--max-time", str(seconds), "--retry", "1",
                           url], check=True, capture_output=True).stdout


def fetch(url, start, stop, etag=None):
    headers = {"Range": f"bytes={start}-{stop-1}", "User-Agent": "Euclid-DR1F-image-research/1"}
    if etag:
        headers["If-Match"] = etag
    request = Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 206:
                    raise ValueError(f"Expected partial content in {url}")
                actual = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",
                                      response.headers.get("Content-Range", ""))
                tag = response.headers.get("ETag")
                if (not actual or tuple(map(int, actual.groups()[:2])) != (start, stop-1)
                        or not tag or (etag and tag != etag)):
                    raise ValueError(f"Unverified range {start}:{stop} in {url}")
                data = response.read(stop-start+1)
            if len(data) != stop-start:
                raise OSError(f"Incomplete response for {start}:{stop} in {url}")
            return data, int(actual[3]), tag
        except (OSError, IncompleteRead) as exc:
            if attempt == 3 or isinstance(exc, HTTPError) and exc.code in (403, 404, 412, 416):
                raise
            time.sleep(0.5 * 2**attempt)



def header(url):
    raw, total, etag = fetch(url,0,28800)
    end = next(i for i in range(0,len(raw),80) if raw[i:i+8] == b"END     ")
    size = ((end+80+2879)//2880)*2880
    data = raw[:size]
    return fits.Header.fromstring(data.decode("ascii"), sep=""), size, {
        "url":url,"etag":etag,"bytes":total,"header_sha256":hashlib.sha256(data).hexdigest()}


def product(tile, band):
    directory, token = {"VIS":("VIS","VIS"),"J":("NISP","NIR-J"),
                        "i2":("HSC","WISHES-I2")}[band]
    params = urlencode({"list-type": 2, "prefix": f"dr1/MER/{tile}/{directory}/"})
    root = ET.fromstring(get(f"{BUCKET}/?{params}"))
    if root.findtext("{*}IsTruncated") == "true":
        raise ValueError("Truncated product list")
    keys = [k.text for k in root.findall(".//{*}Key") if f"_BGSUB-MOSAIC-{token}_" in k.text
            and k.text.endswith(".fits")]
    choices = []
    for key in keys:
        h, size, meta = header(f"{BUCKET}/{key}")
        if "-DATA_RELEASE_DEEP-" in h.get("PPLANID",""):
            choices.append((h,size,meta))
    if len(choices) != 1:
        raise ValueError(f"Expected one deep {band} product for {tile}, found {len(choices)} of {len(keys)}")
    h, size, meta = choices[0]
    if h["NAXIS"] != 2 or h["BITPIX"] != -32 or not h["NAXIS1"] >= WIDTH or not h["NAXIS2"] >= WIDTH:
        raise ValueError(f"Unexpected layout for {meta['url']}")
    meta.update(plan=h["PPLANID"], unit=h.get("BUNIT"), magzero=h.get("MAGZERO"),
                date_obs=h.get("DATE-OBS"), shape=[h["NAXIS2"],h["NAXIS1"]])
    return h,size,meta


def rows(product_info, first, last, workers=4):
    h, hs, meta = product_info
    stride = h["NAXIS1"]*4
    spans = [(a,min(a+512,last)) for a in range(first,last,512)]

    def one(pair):
        a,b=pair
        start,stop=hs+a*stride,hs+b*stride
        data, _, _ = fetch(meta["url"],start,stop,meta["etag"])
        return np.frombuffer(data,dtype=">f4").reshape(b-a,h["NAXIS1"]), {
            "start":start,"end_exclusive":stop,"sha256":hashlib.sha256(data).hexdigest()}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(one,spans):
            yield result


def image_strip(tile, band, cache):
    import json
    stem = cache / f"{tile}-{band}"
    image_path, meta_path, header_path = (stem.with_suffix(e) for e in (".npy",".json",".hdr"))
    if image_path.exists() and meta_path.exists() and header_path.exists():
        result = json.loads(meta_path.read_text())
        return np.load(image_path,mmap_mode="r"), fits.Header.fromstring(header_path.read_text(),sep="\n"), result
    p = product(tile,band)
    h, _, meta = p
    x0=(h["NAXIS1"]-WIDTH)//2
    y0=(h["NAXIS2"]-WIDTH)//2
    target=np.lib.format.open_memmap(stem.with_suffix(".part"),mode="w+",dtype=np.float32,shape=(WIDTH,WIDTH))
    manifest=[]
    row=0
    for data, raw in rows(p,y0,y0+WIDTH):
        target[row:row+len(data)]=data[:,x0:x0+WIDTH]*h.get("BSCALE",1)+h.get("BZERO",0)
        row+=len(data)
        manifest.append(raw)
    target.flush()
    stem.with_suffix(".part").replace(image_path)
    meta.update(ranges=manifest,origin_xy=[x0,y0],shape_analysed=[WIDTH,WIDTH])
    header_path.write_text(h.tostring(sep="\n",padding=False))
    meta_path.write_text(json.dumps(meta))
    return target,h,meta


def window(product_info, x, y, radius):
    h, _, meta=product_info
    x0, y0 = int(np.floor(x))-radius, int(np.floor(y))-radius
    x1, y1 = x0+2*radius+1,y0+2*radius+1
    if min(x0,y0)<0 or x1>h["NAXIS1"] or y1>h["NAXIS2"]:
        raise ValueError("Target window outside mosaic")
    pieces = list(rows(product_info,y0,y1,workers=1))
    a = np.vstack([d[:,x0:x1] for d, _ in pieces]).astype(np.float32)
    return a*h.get("BSCALE",1)+h.get("BZERO",0),(x0,y0),[m for _,m in pieces]
