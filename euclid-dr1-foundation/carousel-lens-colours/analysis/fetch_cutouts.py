"""Retrieve observed Carousel Lens cutouts from public DR1-Foundation MER FITS files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

BASE = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com/"
CENTRE = (90.985416667, -35.9683)
HALF_WIDTH = 280
FITS_BLOCK = 2880


def get_range(url, start, stop):
    byte_range = f"bytes={start}-{stop-1}"
    with urlopen(Request(url, headers={"Range": byte_range}), timeout=75) as response:
        if response.status != 206 or not response.headers.get("Content-Range", "").startswith(
            f"{byte_range.replace('=', ' ')}/"
        ):
            raise OSError(f"Archive did not return the requested byte range for {url}")
        data = response.read(stop-start+1)
    if len(data) != stop-start:
        raise OSError(f"Incomplete archive response for {url}")
    return data


def cut(item, output):
    label, key = item
    url = BASE + key
    raw_header = get_range(url, 0, 10*FITS_BLOCK)
    end = next(i for i in range(0, len(raw_header), 80)
               if raw_header[i:i+8] == b"END     ") + 80
    header = fits.Header.fromstring(raw_header[:end].decode("ascii"), sep="")
    if header["NAXIS"] != 2 or header.get("BSCALE", 1) != 1 or header.get("BZERO", 0) != 0:
        raise ValueError(f"Unexpected FITS layout for {key}")
    dtype = np.dtype({-32: ">f4", 32: ">i4"}[header["BITPIX"]])
    nx, ny = header["NAXIS1"], header["NAXIS2"]
    wcs = WCS(header).celestial
    x, y = (round(float(value)) for value in wcs.world_to_pixel_values(*CENTRE))
    size = HALF_WIDTH
    if not (size <= x <= nx-size and size <= y <= ny-size):
        raise ValueError(f"Cutout crosses a tile edge for {key}")
    offset = ((end+FITS_BLOCK-1)//FITS_BLOCK)*FITS_BLOCK
    start = offset + (y-size)*nx*dtype.itemsize
    stop = start + 2*size*nx*dtype.itemsize
    stripe = np.frombuffer(get_range(url, start, stop), dtype).reshape(2*size, nx)
    image = stripe[:, x-size:x+size].copy()
    cut_header = wcs.slice(np.s_[y-size:y+size, x-size:x+size]).to_header()
    for keyword in ("BUNIT", "MAGZERO", "PHOTZP", "ZP", "FLXSCALE", "EXPTIME", "FILTER"):
        if keyword in header:
            cut_header[keyword] = header[keyword]
    fits.writeto(output/f"{label}.fits", image, cut_header, overwrite=True)
    return label, {
        "key": key, "start": start, "stop": stop, "shape": list(image.shape),
        "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    products = json.loads(args.products.read_text())
    with ThreadPoolExecutor(len(products)) as pool:
        index = dict(pool.map(partial(cut, output=args.output), products.items()))
    (args.output/"cutout_index.json").write_text(json.dumps(index, indent=2)+"\n")


if __name__ == "__main__":
    main()
