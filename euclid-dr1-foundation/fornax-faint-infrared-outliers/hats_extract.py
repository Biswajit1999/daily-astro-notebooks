"""Extract the preregistered MER region from the public IRSA HATS mirror."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
import numpy as np
import pyarrow as pa
import pyarrow.csv
import pyarrow.parquet as pq
import requests

from screen import CENTER, RADIUS, COLUMNS, flux, now

BUCKET = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com"
ROOT = f"{BUCKET}/contributed/dr1/hats/reformatted_catalogs"
CAT = "mer_catalogue_deep_survey"


def partitions(catalog, ra, dec, radius):
    base = f"{ROOT}/{catalog}/euclid_dr1_reformatted_catalogs_{catalog}-hats"
    url = f"{base}/partition_info.csv"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    pixels = {}
    selected = []
    for row in csv.DictReader(io.StringIO(response.text)):
        order, pixel = int(row["Norder"]), int(row["Npix"])
        if order not in pixels:
            hp = HEALPix(nside=2**order, order="nested")
            pixels[order] = set(hp.cone_search_lonlat(ra*u.deg, dec*u.deg, radius*u.deg))
        if pixel in pixels[order]:
            key = f"Norder={order}/Dir={row['Dir']}/Npix={pixel}"
            selected.append((f"{base}/dataset/{key}/part0.snappy.parquet", int(row["num_rows"])))
    return url, response.content, selected


def fetch_range(url, interval, etag=None):
    start, end = interval
    args = ["curl", "-fsSL", "--retry", "2", "--retry-delay", "1", "--max-time", "25",
            "-D", "/dev/stderr", "-r", f"{start}-{end}" if start >= 0 else str(start)]
    if etag:
        args.extend(["-H", f"If-Match: {etag}"])
    result = subprocess.run([*args, url], check=True, capture_output=True)
    headers = result.stderr.decode().splitlines()
    range_header = next((line.split(":", 1)[1].strip() for line in reversed(headers)
                         if line.lower().startswith("content-range:")), "")
    content_range = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", range_header)
    if content_range is None:
        raise ValueError(f"Archive did not return a byte range: {url}")
    first, last, size = map(int, content_range.groups())
    expected = (start, end) if start >= 0 else (size+start, size-1)
    data = result.stdout
    if (first, last) != expected or len(data) != last-first+1:
        raise ValueError(f"Unexpected Content-Range for {url}")
    actual_etag = next((line.split(":", 1)[1].strip() for line in reversed(headers)
                        if line.lower().startswith("etag:")), None)
    if etag and etag != actual_etag:
        raise ValueError("Source ETag differs across range reads")
    return data, size, actual_etag


def range_parquet(url, cache, columns):
    tail, size, etag = fetch_range(url, (-8, None))
    footer_size, magic = struct.unpack("<I4s", tail)
    if magic != b"PAR1" or not 0 < footer_size < 10_000_000 or not etag:
        raise ValueError("Invalid Parquet footer or missing source ETag")
    footer_start = size - footer_size - 8
    footer, _, _ = fetch_range(url, (footer_start, size-1), etag)
    metadata = pq.read_metadata(pa.BufferReader(b"PAR1" + footer))
    intervals = []
    chosen_groups = []
    for i in range(metadata.num_row_groups):
        group = metadata.row_group(i)
        chunks = {group.column(j).path_in_schema: group.column(j)
                  for j in range(group.num_columns)}
        dec = chunks["dec"].statistics
        if dec is not None and (dec.max < CENTER[1]-RADIUS or dec.min > CENTER[1]+RADIUS):
            continue
        chosen_groups.append(i)
        for name in columns:
            c = chunks[name]
            start = c.dictionary_page_offset or c.data_page_offset
            intervals.append((start, start+c.total_compressed_size-1))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]+350000:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    identity = hashlib.sha256(f"{url} {etag}".encode()).hexdigest()
    local = cache / f"{identity}.parquet"
    checksums = [{"start": footer_start, "end": size-1,
                  "sha256": hashlib.sha256(footer).hexdigest()}]
    with local.open("wb") as stream, ThreadPoolExecutor(max_workers=12) as workers:
        stream.write(b"PAR1")
        stream.seek(footer_start)
        stream.write(footer)

        def get(interval):
            return fetch_range(url, interval, etag)[0]

        for (start, end), data in zip(merged, workers.map(get, merged), strict=True):
            stream.seek(start)
            stream.write(data)
            checksums.append({"start": start, "end": end, "sha256": hashlib.sha256(data).hexdigest()})
    return local, chosen_groups, {"url": url, "etag": etag, "source_bytes": size,
                                  "row_groups": chosen_groups, "ranges": checksums}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    started = now()
    url, index, sources = partitions(CAT, *CENTER, RADIUS)
    if not sources:
        raise ValueError("The IRSA HATS partition index lists no coverage for the specified cone")
    target = SkyCoord(*CENTER, unit="deg")
    columns = [name for name in COLUMNS if name != "cntr"]
    inputs = []
    total_cone = 0
    synthetic_row_key = 0
    raw = io.BytesIO()
    output_schema = None
    writer = None
    for path, published_count in sources:
        file, groups, manifest = range_parquet(path, args.cache, columns)
        parquet = pq.ParquetFile(file, memory_map=True)
        if parquet.metadata.num_rows != published_count:
            raise ValueError(f"Parquet row count differs from the partition index: {path}")
        for batch in parquet.iter_batches(batch_size=131072, row_groups=groups, columns=columns):
            tab = pa.Table.from_batches([batch])
            ra, dec = tab["ra"].to_numpy(), tab["dec"].to_numpy()
            # Loose prefilter only. The final selection uses great-circle separation.
            approx = np.isfinite(ra) & np.isfinite(dec)
            approx &= (np.abs(ra-CENTER[0]) < 2*RADIUS) & (np.abs(dec-CENTER[1]) <= RADIUS)
            indices = np.flatnonzero(approx)
            pos = SkyCoord(ra[indices]*u.deg, dec[indices]*u.deg)
            inside = indices[target.separation(pos).deg <= RADIUS]
            total_cone += len(inside)
            reduced = tab.take(inside)
            j = reduced["flux_j_templfit"].to_numpy().astype(np.float64)
            chosen = np.flatnonzero((j >= flux(24)) & (j < flux(23)))
            sub = reduced.take(chosen)
            # TAP's cntr is absent in HATS. This local row ordinal is solely a deterministic tie-break key.
            sub = sub.append_column("cntr", pa.array(synthetic_row_key + inside[chosen], type=pa.int64()))
            if output_schema is None:
                output_schema = sub.schema
                writer = pyarrow.csv.CSVWriter(raw, output_schema)
            writer.write_table(sub)
            synthetic_row_key += len(batch)
        inputs.append({**manifest, "partition_catalogue_rows": published_count})
    writer.close()
    payload = raw.getvalue()
    (args.output / "mer_raw.csv.gz").write_bytes(gzip.compress(payload, mtime=0))
    (args.output / "hats_partition_info.csv").write_bytes(index)
    provenance = {"started_utc": started, "completed_utc": now(), "partition_index_url": url,
                  "partition_index_sha256": hashlib.sha256(index).hexdigest(),
                  "cone_rows_before_j_cut": total_cone, "inputs": inputs,
                  "hats_cntr_note": "Sequential local row ordinal, not an IRSA catalogue ID."}
    (args.output / "hats_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
