"""Download the pinned Euclid and DESI data products (approximately 1.72 GB)."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

from analyse import SOURCES, input_hashes


def fetch(cache, name, url):
    path = cache/name
    if path.exists():
        return
    partial = path.with_suffix(path.suffix+".part")
    subprocess.run(["curl", "-fLsS", "--retry", "2", "--max-time", "900", url, "-o", str(partial)], check=True)
    partial.replace(path)
    print(f"{name}: {path.stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for job in [pool.submit(fetch, args.cache, name, url) for name, url in SOURCES.items()]:
            job.result()
    input_hashes(args.cache)
