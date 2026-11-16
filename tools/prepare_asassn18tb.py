"""Download and freeze the ASASSN-18tb TESS and DES products for Batch 11."""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "asassn18tb_tess"
RA, DEC = 64.526108, -63.615069


def fetch(url: str, target: Path) -> None:
    if not target.exists():
        print("GET", url)
        urllib.request.urlretrieve(url, target)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetch("https://tess.mit.edu/public/tesstransients/light_curves/lc_2018fhw_cleaned",
          OUT / "lc_2018fhw_cleaned.txt")

    for sector in (1, 2):
        url = ("https://mast.stsci.edu/tesscut/api/v0.1/astrocut?"
               f"ra={RA}&dec={DEC}&x=15&y=15&units=px&sector={sector}")
        archive = OUT / f"tesscut_sector{sector}.zip"
        fetch(url, archive)
        with zipfile.ZipFile(archive) as bundle:
            name = bundle.namelist()[0]
            target = OUT / f"tesscut_sector{sector}.fits"
            if not target.exists():
                with bundle.open(name) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
        archive.unlink()

    base = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
    for band in "gri":
        params = urllib.parse.urlencode({"hips": f"CDS/P/DES-DR2/{band}", "width": 256,
            "height": 256, "fov": 0.03, "projection": "TAN", "coordsys": "icrs",
            "ra": RA, "dec": DEC, "format": "fits"})
        fetch(f"{base}?{params}", OUT / f"des_dr2_{band}.fits")

    readme = """# ASASSN-18tb / SN 2018fhw time-domain data

This directory freezes two 15x15-pixel TESSCut target-pixel files from MAST
(Sectors 1 and 2), the public MIT TESS Transients cleaned light curve, and
DES DR2 g/r/i HiPS cutouts served by CDS. The transient coordinates are
RA 64.526108 deg, Dec -63.615069 deg (ICRS).

TESS pixels are about 21 arcsec wide, so the host galaxy and neighbouring
sources are blended. The notebooks use difference images or baseline-subtracted
flux and do not interpret the raw aperture sum as isolated supernova light.
The MIT file is an automatically processed difference-light-curve product; its
background model and the known scattered-Earthlight intervals are treated as
systematic checks. DES images predate the explosion and describe the host field,
not the supernova at maximum light.

Primary context: Vallely et al. (2019, MNRAS 487, 2372) report a single-power-law
rise index 1.69 +/- 0.04, first light MJD 58341.68 +/- 0.16, B-band maximum
MJD 58357.33 +/- 0.12, and strong late H-alpha emission. The notebooks attempt
an independent compact remeasurement but do not claim a new progenitor result.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    manifest = {"dataset": "ASASSN-18tb / SN 2018fhw TESS time series and DES DR2 host imaging",
        "retrieved_utc": "2026-08-01", "coordinates_icrs_deg": {"ra": RA, "dec": DEC},
        "sources": ["https://mast.stsci.edu/tesscut/",
                    "https://tess.mit.edu/public/tesstransients/",
                    "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"],
        "paper": "https://doi.org/10.1093/mnras/stz1445", "files": []}
    for path in sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json"):
        manifest["files"].append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                                  "sha256": digest(path)})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(manifest['files'])} files")


if __name__ == "__main__":
    main()
