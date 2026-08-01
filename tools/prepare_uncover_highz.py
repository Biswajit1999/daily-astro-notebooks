"""Extract the compact UNCOVER DR3 high-redshift working table.

The upstream FITS catalog is about 84 MB.  This script downloads it only when
needed, verifies the published MD5 checksum, and preserves a small CSV with the
rows and columns used by Batch 9.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.table import Table


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "uncover_dr3_highz"
URL = "https://zenodo.org/records/11059273/files/UNCOVER_DR3_LW_SUPER_catalog.fits?download=1"
MD5 = "baeb44ce166c920050ceb93220b12e05"

CORE = [
    "id", "ra", "dec", "x", "y", "use_phot", "flag_eazy", "flag_star",
    "flag_artifact", "flag_nearbcg", "nusefilt", "z_phot", "z_phot_chi2",
    "z025", "z160", "z500", "z840", "z975", "z_spec", "mu", "mu_low_68",
    "mu_high_68", "flux_radius", "iso_area", "use_aper",
]
FILTERS = ["f090w", "f115w", "f150w", "f200w", "f277w", "f356w", "f444w"]
PHOTOMETRY = [f"{prefix}_{band}" for band in FILTERS for prefix in ("f", "e", "w")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / "UNCOVER_DR3_LW_SUPER_catalog.fits"
    if not source.exists():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, source)

    digest = hashlib.md5(source.read_bytes()).hexdigest()
    if digest != MD5:
        raise SystemExit(f"Checksum mismatch: expected {MD5}, received {digest}")

    table = Table.read(source, hdu=1)
    frame = table[CORE + PHOTOMETRY].to_pandas()
    selected = frame.loc[
        (frame.use_phot == 1)
        & (frame.flag_eazy == 1)
        & np.isfinite(frame.z_phot)
        & frame.z_phot.between(6.0, 15.0, inclusive="left")
    ].copy()
    selected.to_csv(OUT / "uncover_dr3_z6_candidates.csv", index=False, float_format="%.7g")

    manifest = {
        "source": URL,
        "doi": "10.5281/zenodo.11059273",
        "upstream_file": source.name,
        "upstream_md5": MD5,
        "upstream_rows": int(len(frame)),
        "selection": "use_phot == 1 and flag_eazy == 1 and 6 <= z_phot < 15",
        "selected_rows": int(len(selected)),
        "columns": list(selected.columns),
        "retrieved_utc": "2026-08-01",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    source.unlink()  # the compact, checksummed derivative is the repository product
    print(f"Wrote {len(selected):,} rows; removed the temporary 84 MB FITS file")


if __name__ == "__main__":
    main()
