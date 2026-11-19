"""Download two RACS-low DR1 tiles and two Legacy Surveys DR10 r cutouts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from astropy.io import fits
import numpy as np

CADC = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/caom2ops/sync"
LEGACY = "https://www.legacysurvey.org/viewer/fits-cutout"
TILES = ("0304-50A", "0310-56A")


def input_urls():
    urls = {
        f"racs-{tile}.fits": CADC + "?" + urlencode({
            "ID": f"casda:RACS/RACS-DR1_{tile}.fits",
            "CIRCLE": "52.712 -52.525 0.31",
        })
        for tile in TILES
    }
    for suffix, ra, dec, scale, size in (
        ("", 52.712, -52.525, 2, 720),
        ("_lens", 52.737216, -52.470283, 0.4, 500),
    ):
        urls[f"legacy_dr10_r{suffix}.fits"] = LEGACY + "?" + urlencode({
            "ra": ra, "dec": dec, "layer": "ls-dr10",
            "pixscale": scale, "size": size, "bands": "r",
        })
    return urls


def download(item, output):
    name, url = item
    path = output / name
    if path.exists():
        return path
    temporary = path.with_suffix(".part")
    try:
        with urlopen(url, timeout=90) as response:
            data = response.read(12 * 1024 * 1024 + 1)
        if len(data) > 12 * 1024 * 1024 or not data.startswith(b"SIMPLE  ="):
            raise ValueError(f"Expected a bounded FITS cutout from {url}")
        temporary.write_bytes(data)
        with fits.open(temporary, memmap=False) as hdus:
            image = np.squeeze(hdus[0].data)
            if image.ndim != 2 or not np.isfinite(image).any():
                raise ValueError(f"Invalid image in {name}")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path in pool.map(lambda item: download(item, args.output), input_urls().items()):
            print(path)


if __name__ == "__main__":
    main()
