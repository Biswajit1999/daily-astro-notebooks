from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse

from archive import image_strip

TILES = (101829781, 101829782, *range(101830399, 101830409))

def main():
    parser = argparse.ArgumentParser(description="Stage the held-out VIS and J mosaics.")
    parser.add_argument("cache", type=Path)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    cache = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    jobs = [(tile, band) for tile in TILES for band in ("VIS", "J")]

    def fetch_one(tile, band):
        try:
            image, _, meta = image_strip(tile, band, cache)
            return tile, band, image.shape, meta["url"]
        except Exception as exc:
            return tile, band, "error", repr(exc)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(fetch_one, *job) for job in jobs]
        for future in as_completed(pending):
            print(*future.result(), flush=True)

if __name__ == "__main__":
    main()
