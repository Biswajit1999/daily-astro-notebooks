"""Fetch and verify the four recorded images used in the IC 1914 disc fit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"analysis"))

from fetch import extract


def download(record, cache):
    band = record["band"]
    out = cache / f"IC1914_{band}.fits"
    pending = out.with_suffix(".fits.part")
    try:
        if "url" in record:
            with urlopen(record["url"], timeout=60) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != record["file_sha256"]:
                raise ValueError(f"Archive file checksum differs for {band}")
            pending.write_bytes(payload)
        else:
            retrieved = extract(record["key"], 49.8551, -49.59967, pending,
                                half_size=1650, stripe_rows=160 if band=="vis_sky" else 256)
            if retrieved["bounds"] != record["bounds"] or retrieved["pixel_sha256"] != record["pixel_sha256"]:
                raise ValueError(f"Archive pixel checksum or bounds differ for {band}")
        pending.replace(out)
        return band
    finally:
        pending.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    records = json.loads((HERE/"inputs.json").read_text())
    with ThreadPoolExecutor(4) as pool:
        for band in pool.map(lambda record: download(record, args.cache), records):
            print(f"{band} verified")


if __name__ == "__main__":
    main()
