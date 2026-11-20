"""Find DR1-F deep coadds and public PSF data through the IRSA SIA service."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent


def request(target, cache):
    query = urlencode({"POS": f"CIRCLE {target['ra']} {target['dec']} 0.012",
                       "COLLECTION": "euclid_dr1_deep_DpdMerBksMosaic", "MAXREC": 350})
    with urlopen(f"https://irsa.ipac.caltech.edu/SIA?{query}", timeout=30) as response:
        votable = response.read()
    (cache / f"{target['object_id']}.xml").write_bytes(votable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    targets = [target for pair in json.loads((HERE / "targets.json").read_text()) for target in pair]
    with ThreadPoolExecutor(max_workers=6) as executor:
        for job in [executor.submit(request, target, args.cache) for target in targets]:
            job.result()


if __name__ == "__main__":
    main()
