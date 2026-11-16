"""Obtain observed Legacy Survey r-band cutouts matching the Euclid fields."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "https://www.legacysurvey.org/viewer/fits-cutout"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.targets.open() as stream:
        rows = list(csv.DictReader(stream))

    def get(row):
        name = row["object"]
        params = dict(ra=row["ra"], dec=row["dec"], size=480, pixscale=0.5, layer="ls-dr10", bands="r")
        url = BASE + "?" + urlencode(params)
        record = dict(target=name, band="legacy_r", url=url)
        try:
            with urlopen(url, timeout=55) as response:
                data = response.read()
            if not data.startswith(b"SIMPLE  ="):
                raise OSError("Archive did not return a primary FITS image")
            (args.output / f"{name}_legacy_r.fits").write_bytes(data)
            record["file_sha256"] = hashlib.sha256(data).hexdigest()
        except OSError as exc:
            record["error"] = str(exc)
        print(record, flush=True)
        return record

    with ThreadPoolExecutor(4) as pool:
        records = list(pool.map(get, rows))
    (args.output / "cutouts_legacy_r.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
