"""Query public optical spectroscopy in the audited Fornax cone."""
import io
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from astropy.coordinates import SkyCoord
from astropy.io import ascii
from astropy.io.votable import parse_single_table
import numpy as np
import astropy.units as u

from external import request
from audit import ESO
from screen import CENTER, RADIUS, now

TABLES = {
    "VANDELS_SPECTRO_V4": ("id,alpha,delta,zspec,zflg", "alpha", "delta"),
    "GOODS_VIMOS_SPEC_V1": ("ID_VIMOS,RAJ2000_VIMOS,DEJ2000_VIMOS,SPEC_Z", "RAJ2000_VIMOS", "DEJ2000_VIMOS"),
}


def main():
    out = Path("results")
    summary = json.loads((out/"summary.json").read_text())
    targets = summary["audited"]
    center = SkyCoord(*CENTER, unit="deg")
    mer = ascii.read(out/"full_quality_table.csv.gz", format="csv")
    mer_coords = SkyCoord(mer["ra"], mer["dec"], unit="deg")
    report = {"utc": now(), "endpoint": ESO, "catalogues": {}}
    for name, (columns, ra, dec) in TABLES.items():
        query = (f"SELECT TOP 2000 {columns} FROM {name} WHERE "
                 f"{ra} >= {CENTER[0]-1.2*RADIUS} AND {ra} <= {CENTER[0]+1.2*RADIUS} "
                 f"AND {dec} >= {CENTER[1]-RADIUS} AND {dec} <= {CENTER[1]+RADIUS}")
        record = {"adql": query}
        try:
            raw = request(ESO, {"REQUEST":"doQuery", "LANG":"ADQL","FORMAT":"votable","QUERY":query})
            tree = ET.fromstring(raw)
            states = [i for i in tree.findall(".//{*}INFO") if i.get("name") == "QUERY_STATUS"]
            if any(i.get("value") in {"ERROR", "OVERFLOW"} for i in states):
                raise ValueError(" ".join((i.text or "").strip() for i in states))
            table = parse_single_table(io.BytesIO(raw)).to_table(use_names_over_ids=True)
            if len(table) >= 2000:
                raise ValueError("Row cap reached")
            names = {n.lower(): n for n in table.colnames}
            p = SkyCoord(table[names[ra.lower()]], table[names[dec.lower()]], unit="deg")
            use = center.separation(p) <= RADIUS*u.deg
            p, table = p[use], table[use]
            table.write(out / f"{name}.csv", format="ascii.csv", overwrite=True)
            within = {}
            for t in targets:
                separation = SkyCoord(t["ra"],t["dec"],unit="deg").separation(p).arcsec
                within[t["id"]] = {
                    "within_one_arcsec": int((separation <= 1).sum()),
                    "nearest_arcsec": float(min(separation)) if len(separation) else None,
                }
            z = np.ma.asarray(table[names["zspec" if name.startswith("VANDELS") else "spec_z"]],
                              dtype=float).filled(np.nan)
            if len(p):
                i, offset, _ = p.match_to_catalog_sky(mer_coords)
                qualified = (offset.arcsec <= 1) & np.isfinite(z) & (z > 0)
            else:
                qualified = np.zeros(0, dtype=bool)
            record.update(cone_rows=len(table), targets=within,
                          positive_redshift_matches_within_one_arcsec=int(qualified.sum()))
        except (ValueError, OSError, subprocess.CalledProcessError) as e:
            record["error"] = str(e)
        report["catalogues"][name] = record
    (out/"independent_spec.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
