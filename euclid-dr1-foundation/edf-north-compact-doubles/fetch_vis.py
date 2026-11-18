"""Stage the preregistered VIS mosaic regions in parallel."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from archive import TILES, image_strip

if __name__ == "__main__":
    cache=Path(sys.argv[1])
    cache.mkdir(parents=True,exist_ok=True)
    def read(tile):
        try:
            a,h,m=image_strip(tile,sys.argv[2] if len(sys.argv)>2 else "VIS",cache)
            print(tile,a.shape,m["url"],flush=True)
        except Exception as e:
            print(tile,type(e).__name__,str(e),flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(read,TILES))
