"""Read exact MER-ID matches from the DR1-F public PHZ and SPE HATS collections."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import struct
import math

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from astropy.table import Table
import numpy as np
import matplotlib.pyplot as plt

from hats_extract import fetch_range, partitions

CATALOGS = {
    "phz_photo_z_deep_survey": ("phz_median", "phz_70_int_1", "phz_70_int_2",
                                "phz_mode_1", "phz_mode_2", "phz_flags"),
    "phz_classification_deep_survey": ("phz_classification", "phz_star_prob", "phz_gal_prob", "phz_qso_prob"),
    "spectro_z_spe_classification_deep": ("spe_class", "spe_star_prob", "spe_gal_prob", "spe_qso_prob"),
    "spectro_z_spe_galaxy_candidates_deep": ("spe_rank", "spe_z", "spe_z_prob", "spe_z_rel"),
    "sir_combined_spectra": ("tileid", "lrange", "n_dith", "spectrum"),
}


def read_selection(catalog, target_rows, cache, out):
    source_info, _, sources = partitions(catalog, 52.933, -28.0885, 0.13)
    ids = pa.array([t["object_id"] for t in target_rows])
    by_id = {t["object_id"]: t["id"] for t in target_rows}
    found = {name: [] for name in by_id.values()}
    manifest = []
    for url, published_count in sources:
        tail, size, etag = fetch_range(url, (-8, None))
        footer_size, magic = struct.unpack("<I4s", tail)
        if magic != b"PAR1" or not 0 < footer_size < 10_000_000:
            raise ValueError(f"Invalid footer in {url}")
        start = size-footer_size-8
        footer, _, _ = fetch_range(url, (start, size-1), etag)
        meta = pq.read_metadata(pa.BufferReader(b"PAR1"+footer))
        if meta.num_rows != published_count:
            raise ValueError(f"Incomplete partition in {url}")
        path = cache / f"{catalog}-{hashlib.sha256(url.encode()).hexdigest()[:12]}.parquet"
        checks = [{"start": start, "end": size-1, "sha256": hashlib.sha256(footer).hexdigest()}]
        with path.open("wb") as stream:
            stream.write(b"PAR1")
            stream.seek(start)
            stream.write(footer)

        def chunks(group, columns):
            records = {group.column(j).path_in_schema: group.column(j) for j in range(group.num_columns)}
            return [c for k, c in records.items()
                    if any(k == name or k.startswith(name+".") for name in columns)]

        def get(chunk):
            offset = chunk.dictionary_page_offset or chunk.data_page_offset
            end = offset+chunk.total_compressed_size-1
            data, _, _ = fetch_range(url, (offset, end), etag)
            return offset, data

        def fill(work):
            with path.open("r+b") as stream, ThreadPoolExecutor(max_workers=8) as pool:
                for offset, data in pool.map(get, work):
                    stream.seek(offset)
                    stream.write(data)
                    checks.append({"start": offset, "end": offset+len(data)-1,
                                   "sha256": hashlib.sha256(data).hexdigest()})

        root_names = meta.schema.to_arrow_schema().names
        oid = next(n for n in ("object_id", "objectid") if n in root_names)
        columns = [n for n in CATALOGS[catalog] if n in root_names]
        if not columns:
            raise ValueError(f"No expected fields in {catalog}: {root_names}")
        groups = [meta.row_group(i) for i in range(meta.num_row_groups)]
        fill([c for group in groups for c in chunks(group, [oid])])
        index = pq.ParquetFile(path, memory_map=True)
        for i, group in enumerate(groups):
            id_data = index.read_row_group(i, columns=[oid])[oid]
            selected = pc.indices_nonzero(pc.is_in(id_data, value_set=ids))
            if not len(selected):
                continue
            fill(chunks(group, columns))
            data = pq.ParquetFile(path, memory_map=True).read_row_group(i, columns=[oid, *columns])
            for row in data.take(selected).to_pylist():
                found[by_id[row[oid]]].append(row)
        manifest.append({"url": url, "etag": etag, "verified_ranges": checks,
                         "fields": [oid, *columns], "published_count": published_count})
    for target, rows in found.items():
        if rows and catalog != "sir_combined_spectra":
            Table(rows=rows).write(out / target / f"{catalog}.csv", format="ascii.csv", overwrite=True)
    return {"partition_index": source_info, "sources": manifest, "rows": found}


def json_compatible(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, list):
        return [json_compatible(item) for item in value]
    if isinstance(value, dict):
        return {key: json_compatible(item) for key, item in value.items()}
    return value


def plot_spectra(matches, out):
    for target, rows in matches.items():
        if not rows:
            continue
        fig, ax = plt.subplots(figsize=(7.5, 3.0), layout="constrained")
        for row in rows:
            data = row.get("spectrum") or {}
            if not all(data.get(k) is not None for k in ("wavelength", "signal", "var", "mask")):
                continue
            w, f, var, mask = (np.asarray(data[k], dtype=float) for k in ("wavelength", "signal", "var", "mask"))
            use = np.isfinite(w) & np.isfinite(f) & np.isfinite(var) & (var > 0)
            if not use.any():
                continue
            if not 8000 < np.median(w[use]) < 22000:
                raise ValueError("Unexpected SIR wavelength scale (expected Angstrom)")
            wave = w[use] / 1e4
            snr = f[use] / np.sqrt(var[use])
            clean = mask[use] == 0
            ax.plot(wave, snr, lw=.45, color="#8599a4", alpha=.45)
            ax.scatter(wave[clean], snr[clean], s=3, label=str(row.get("lrange", "NISP")))
        ax.axhline(0, color="#283942", lw=.55)
        ax.set(xlabel="Wavelength (µm)", ylabel="Signal / formal σ per bin", title=f"{target} · Euclid NISP combined spectrum")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)
            fig.savefig(out / target / "spectrum.png", dpi=155)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--catalog", nargs="+", choices=CATALOGS, default=list(CATALOGS))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    summary = json.loads((args.results / "summary.json").read_text())
    targets = summary["audited"]
    out = args.results / "audit"
    for target in targets:
        (out / target["id"]).mkdir(parents=True, exist_ok=True)

    def one(catalog):
        try:
            record = read_selection(catalog, targets, args.cache, out)
            if catalog == "sir_combined_spectra":
                # JSON preserves the same data as the plot, including masks and unplotted bins.
                (args.results / "nisp_spectra.json").write_text(json.dumps(json_compatible(record["rows"]), allow_nan=False, separators=(",", ":"))+"\n")
                plot_spectra(record["rows"], out)
            result = {**record, "rows": {target: len(v) for target, v in record["rows"].items()}}
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"}
        (args.results / f"hats_{catalog}.json").write_text(json.dumps(result, indent=2)+"\n")
        print(catalog, result.get("rows", result.get("error")), flush=True)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(one, args.catalog))


if __name__ == "__main__":
    main()
