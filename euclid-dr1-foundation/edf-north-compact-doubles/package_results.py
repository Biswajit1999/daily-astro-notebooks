"""Compress complete ranked candidates and split the signed pair table by tile."""
import csv
import gzip
import io
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def write_gzip(path):
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as archive:
            with io.TextIOWrapper(archive, newline="", encoding="utf-8") as text:
                yield text


def package(results=Path("results")):
    with (results / "candidates.csv").open(newline="") as original:
        with write_gzip(results / "candidates.csv.gz") as archive:
            for line in original:
                archive.write(line)
    directory = results / "signed"
    directory.mkdir(exist_ok=True)
    with gzip.open(results / "signed_vis_pairs.csv.gz", "rt", newline="") as archive:
        rows = csv.DictReader(archive)
        groups = {}
        for row in rows:
            groups.setdefault((row["tile"], row["sign"]), []).append(row)
        for (tile, sign), records in sorted(groups.items()):
            with write_gzip(directory / f"{tile}_{'pos' if sign == '1' else 'neg'}.csv.gz") as text:
                out = csv.DictWriter(text, rows.fieldnames)
                out.writeheader()
                out.writerows(records)


if __name__ == "__main__":
    package()
