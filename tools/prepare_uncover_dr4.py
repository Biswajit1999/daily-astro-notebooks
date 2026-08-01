"""Prepare compact UNCOVER DR4.1 spectroscopy products for Batch 10."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "uncover_dr4_spectroscopy"


def read_ascii(path: Path) -> pd.DataFrame:
    names = path.read_text(encoding="utf-8").splitlines()[0].lstrip("#").split()
    return pd.read_csv(path, sep=r"\s+", comment="#", header=None, names=names,
                       na_values=[-99, -9999])


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spectra").mkdir(exist_ok=True)
    (OUT / "cutouts").mkdir(exist_ok=True)

    zspec = read_ascii(Path("/tmp/uncover-zspec.dat"))
    lines = read_ascii(Path("/tmp/uncover-lines.dat"))
    magnification = read_ascii(Path("/tmp/uncover-magnifications.dat"))
    phot = pd.read_csv(ROOT / "data/uncover_dr3_highz/uncover_dr3_z6_candidates.csv")

    secure = zspec[zspec.flag_zspec_qual.isin([2, 3])].copy()
    secure.to_csv(OUT / "dr4_secure_redshifts.csv", index=False)
    high = secure[secure.z_spec >= 6].copy()
    high_lines = high.merge(lines, on=["id_msa", "z_spec"], how="left")
    high_lines.to_csv(OUT / "dr4_highz_line_fluxes.csv", index=False)
    high.merge(magnification, on="id_msa", how="left").to_csv(
        OUT / "dr4_highz_magnifications.csv", index=False)

    matched = phot.merge(secure, left_on="id", right_on="id_DR3", how="inner",
                         suffixes=("_dr3", "_dr4"))
    matched.to_csv(OUT / "dr3_dr4_highz_crossmatch.csv", index=False)

    for source in sorted(Path("/tmp/uncover-specs").glob("*.fits")):
        shutil.copy2(source, OUT / "spectra" / source.name)
    shutil.copy2("/tmp/README_DR4.1_spec.txt", OUT / "UPSTREAM_README_DR4.1.txt")

    files = sorted(path for path in OUT.rglob("*") if path.is_file())
    manifest = {
        "dataset": "UNCOVER DR4.1 spectroscopy and DR3 photometric cross-match",
        "retrieved_utc": "2026-08-01",
        "official_release": "https://jwst-uncover.github.io/DR4.html",
        "paper": "https://arxiv.org/abs/2408.03920",
        "selection": "flag_zspec_qual in {2,3}; high-z tables additionally require z_spec >= 6",
        "units": {"spectrum_wave": "micrometre", "spectrum_flux": "microjansky",
                  "line_flux": "1e-20 erg s-1 cm-2; not corrected for lens magnification"},
        "counts": {"targets": int(len(zspec)), "successful_spectra": int(zspec.flag_successful_spectrum.eq(1).sum()),
                   "secure_or_solid": int(len(secure)), "secure_or_solid_z_ge_6": int(len(high)),
                   "dr3_highz_crossmatches": int(len(matched))},
        "files": [],
    }
    for path in files:
        manifest["files"].append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                                  "sha256": sha256(path)})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readme = """# UNCOVER DR4.1 spectroscopy derivative

This directory freezes the public UNCOVER DR4.1 redshift, line-flux, lens-model,
and representative spectrum products used by the 1 August 2026 notebooks.
Rows with `flag_zspec_qual` 2 or 3 are described as solid or secure, following
the release. Line fluxes retain the release units and are **not** corrected for
lensing magnification. The six FITS files are the release's recommended default
1D/2D spectra, not the separately supplied photometric-rescaled variants.

The cross-match joins the earlier DR3 high-redshift candidate table on its
catalogue ID (`id`) and DR4's `id_DR3`. It is an audit of the photometric
selection, not a complete or random spectroscopic sample: NIRSpec targets were
selected for several science programmes and the unmatched candidates have no
spectroscopic verdict here.

Sources: the [official DR4.1 release](https://jwst-uncover.github.io/DR4.html),
Price et al. (2025), Suess et al. (2024), and the Furtak et al. lens model.
Exact file sizes and checksums are recorded in `manifest.json`.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    # Rebuild the inventory after all products exist. The manifest does not
    # checksum itself, which keeps every recorded digest stable and verifiable.
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest["files"] = [
        {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
