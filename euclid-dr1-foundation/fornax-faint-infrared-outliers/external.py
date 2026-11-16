"""Archive independent Gaia, WISE and VIRCAM source searches."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from astropy.coordinates import SkyCoord
from astropy.io import ascii
from astropy.io.votable import parse_single_table

from audit import ESO
from screen import cone, now

GAIA = "https://gea.esac.esa.int/tap-server/tap/sync"
GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"


def request(url, data):
    args = [item for k, v in data.items() for item in ("--data-urlencode", f"{k}={v}")]
    result = subprocess.run(["curl", "-fsSLG", "--max-time", "36", *args, url],
                            capture_output=True, check=True)
    return result.stdout


def eso_query(ra, dec, dataset):
    # ESO's CONTAINS translation returned a SQL syntax error. Source lists use a
    # padded rectangular request, with the actual 10 arcsec circle applied locally.
    a = 12.0/3600
    box = (f"RA2000 >= {ra-a:.12f} AND RA2000 <= {ra+a:.12f} "
           f"AND DEC2000 >= {dec-a:.12f} AND DEC2000 <= {dec+a:.12f}")
    if dataset == "VIDEO_CAT_DR5":
        base = ["VIDEOID", "IAUNAME", "FIELDNAME", "RA2000", "DEC2000"]
        fields = [f"{b}_{kind}_APER_3" for b in ("Z", "Y", "J", "H", "KS")
                  for kind in ("MAG", "MAGERR")]
        fields += [f"{b}_FLAGS" for b in ("Z", "Y", "J", "H", "KS")]
    else:
        base = ["SOURCEID", "SOURCENAME", "FRAMESETID", "RA2000", "DEC2000"]
        fields = [f"{b}APERMAG3{salt}" for b in ("Y", "J", "H", "KS") for salt in ("", "ERR")]
    return f"SELECT TOP 999 {','.join(base+fields)} FROM {dataset} WHERE {box}"


def collect(target, folder):
    ra, dec = target["ra"], target["dec"]
    pos = SkyCoord(ra, dec, unit="deg")
    queries = {
        "gaia_dr3": (GAIA, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                           "QUERY": ("SELECT source_id,ra,dec,ref_epoch,parallax,parallax_error,"
                                     "pmra,pmdec,pmra_error,pmdec_error,ruwe,phot_g_mean_mag "
                                     f"FROM gaiadr3.gaia_source WHERE {cone(ra, dec, 10/3600)}")}, "csv"),
        "catwise2020": (GATOR, {"catalog": "catwise_2020", "objstr": f"{ra} {dec}", "spatial": "cone",
                                "radius": 10, "radunits": "arcsec", "outfmt": 1}, "tbl"),
        **{name: (ESO, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable",
                         "QUERY": eso_query(ra, dec, name)}, "xml")
           for name in ("VIDEO_CAT_DR5", "VHS_CAT_V3")},
    }

    def run(task):
        name, (url, params, ext) = task
        rec = {"endpoint": url, "parameters": params}
        try:
            raw = request(url, params)
            file = folder / f"{name}.{ext}"
            file.write_bytes(raw)
            if ext == "csv":
                reader = csv.DictReader(io.StringIO(raw.decode()))
                if not reader.fieldnames or "source_id" not in reader.fieldnames:
                    raise ValueError("Gaia response had no expected column header")
                rows = list(reader)
                rec.update(rows=len(rows), matches=rows)
            elif ext == "tbl":
                table = ascii.read(raw.decode().splitlines(), format="ipac", guess=False)
                if "source_id" not in table.colnames:
                    raise ValueError("CatWISE response had no expected column header")
                cols = ("source_name", "source_id", "dist", "w1mpro", "w2mpro", "w1snr", "w2snr",
                        "pmra", "pmdec", "sigpmra", "sigpmdec", "cc_flags", "ab_flags")
                rows = [{col: str(r[col]) for col in cols if col in table.colnames} for r in table]
                rec.update(rows=len(rows), matches=rows)
            else:
                root = ET.fromstring(raw)
                states = [i for i in root.findall(".//{*}INFO") if i.get("name") == "QUERY_STATUS"]
                if any(i.get("value") in {"ERROR", "OVERFLOW"} for i in states):
                    raise ValueError(" ".join((i.text or "").strip() for i in states))
                table = parse_single_table(io.BytesIO(raw)).to_table(use_names_over_ids=True)
                if len(table) >= 999:
                    raise ValueError("ESO row cap reached")
                names = {k.upper(): k for k in table.colnames}
                coords = SkyCoord(table[names["RA2000"]], table[names["DEC2000"]], unit="deg")
                sep = pos.separation(coords).arcsec
                table["angular_separation_arcsec"] = sep
                local = table[sep <= 10]
                local.sort("angular_separation_arcsec")
                csv_file = folder / f"{name}_cone.csv"
                local.write(csv_file, format="ascii.csv", overwrite=True)
                rec.update(rows=len(local), box_rows=len(table),
                           matches=[{col: str(r[col]) for col in local.colnames} for r in local])
        except (subprocess.CalledProcessError, ValueError, OSError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                rec["error"] = exc.stderr.decode()[:350]
            else:
                rec["error"] = str(exc)[:350]
        return name, rec

    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(run, queries.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    args = parser.parse_args()
    targets = json.loads((args.results / "summary.json").read_text())["audited"]

    def one(t):
        path = args.results / "audit" / t["id"]
        path.mkdir(parents=True, exist_ok=True)
        return t["id"], collect(t, path)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(one, targets))
    (args.results / "external_audit.json").write_text(json.dumps({"utc": now(), "targets": results}, indent=2)+"\n")


if __name__ == "__main__":
    main()
