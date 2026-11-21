"""Stream and reduce public AbacusSummit DR1 LRG mock FITS catalogues."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

from astropy.io import fits
from mocpy import MOC
import numpy as np

from analyse import CAPS, MASK_FILES, SOURCES, in_masks

BASE = "https://data.desi.lbl.gov/public/dr1/survey/catalogs/dr1/mocks/AbacusSummit/dark/v4.2/"
MOCKS = tuple(range(8))
COLUMNS = ("RA", "DEC", "Z", "WEIGHT", "WEIGHT_FKP")
Z = (.6, .8)
FULL_KEEP = {"galaxy": .25, "random": .055}
SEED = 20261121


def header(read):
    cards = bytearray()
    while True:
        block = read(2880)
        if len(block) != 2880:
            raise ValueError("Incomplete FITS header")
        cards.extend(block)
        if any(block[i:i+8] == b"END     " for i in range(0, 2880, 80)):
            return fits.Header.fromstring(cards.decode("ascii"), sep="")


def reduce_fits(stream, mask, seed, kind):
    digest = hashlib.sha256()
    count = 0

    def read(size):
        nonlocal count
        block = stream.read(size)
        digest.update(block)
        count += len(block)
        return block

    primary = header(read)
    h = header(read)
    if primary["NAXIS"] != 0 or h["XTENSION"] != "BINTABLE" or h["PCOUNT"] != 0:
        raise ValueError("Unexpected Abacus FITS layout")
    columns = fits.ColDefs([fits.Column(name=h[f"TTYPE{i}"], format=h[f"TFORM{i}"],
                                       bscale=h.get(f"TSCAL{i}"), bzero=h.get(f"TZERO{i}"))
                            for i in range(1, h["TFIELDS"]+1)])
    dtype = columns.dtype.newbyteorder(">")
    if dtype.itemsize != h["NAXIS1"] or any(
        n not in dtype.names or columns[n].bscale not in (None, 1) or columns[n].bzero not in (None, 0)
        for n in COLUMNS
    ):
        raise ValueError("Unexpected selected column layout or FITS scaling")
    rng = np.random.default_rng(seed)
    full, overlap = [], []
    eligible = 0
    for start in range(0, h["NAXIS2"], 250_000):
        length = min(h["NAXIS2"]-start, 250_000)*dtype.itemsize
        block = read(length)
        if len(block) != length:
            raise ValueError(f"Incomplete FITS table at row {start}")
        table = np.frombuffer(block, dtype=dtype)
        z = table["Z"]
        valid = (z >= Z[0]) & (z < Z[1]) & (table["WEIGHT"] > 0) & (table["WEIGHT_FKP"] > 0)
        selected = table[valid]
        eligible += len(selected)
        data = np.column_stack([selected[n] for n in COLUMNS])
        if not np.all(np.isfinite(data)):
            raise ValueError("Nonfinite coordinates or weights in selected rows")
        flag = in_masks({"RA": data[:, 0], "DEC": data[:, 1]}, {"mer_wide": mask})[:, 0]
        full.append(data[rng.random(len(data)) < FULL_KEEP[kind]])
        overlap.append(data[flag])
    pad = (-count) % 2880
    if len(read(pad)) != pad or read(1):
        raise ValueError("Unexpected FITS table padding or extra HDU")
    return np.concatenate(full), np.concatenate(overlap), {
        "sha256": digest.hexdigest(), "bytes": count, "fits_rows": h["NAXIS2"], "eligible_rows": eligible,
    }


def fetch_one(cache, mask, mock, cap, kind):
    suffix = "clustering.dat" if kind == "galaxy" else "0_clustering.ran"
    url = f"{BASE}mock{mock}/LRG_complete_{cap}_{suffix}.fits"
    target = cache/f"mock{mock}-{cap}-{kind}.npz"
    if target.exists():
        return
    seed = [SEED, mock, CAPS.index(cap), int(kind == "random")]
    for attempt in range(3):
        command = ["curl", "-fLsS", "--max-time", "250", url]
        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
                try:
                    full, overlap, meta = reduce_fits(process.stdout, mask, seed, kind)
                except BaseException:
                    process.kill()
                    raise
                if process.wait() != 0:
                    raise ValueError("Archive transfer failed")
            break
        except (OSError, ValueError) as exc:
            if attempt == 2:
                raise RuntimeError(url) from exc
            time.sleep(1+attempt)
    meta.update(url=url, full_rows=len(full), overlap_rows=len(overlap))
    temp = target.with_suffix(".part.npz")
    np.savez_compressed(temp, full=full, overlap=overlap, metadata=json.dumps(meta))
    temp.replace(target)
    print(f"mock {mock:02d} {cap} {kind}: {len(full):,} full, {len(overlap):,} overlap", flush=True)


def get_mask(cache):
    name = MASK_FILES["mer_wide"]
    path = cache/name
    if not path.exists():
        temp = path.with_suffix(".part")
        subprocess.run(["curl", "-fLsS", "--max-time", "45", SOURCES[name], "-o", str(temp)], check=True)
        temp.replace(path)
    return MOC.from_fits(path)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--mocks", type=int, nargs="+", default=MOCKS)
    parser.add_argument("--jobs", type=int, default=5)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    mask = get_mask(args.cache)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        jobs = [pool.submit(fetch_one, args.cache, mask, mock, cap, kind)
                for mock in args.mocks for cap in CAPS for kind in FULL_KEEP]
        for job in jobs:
            job.result()
