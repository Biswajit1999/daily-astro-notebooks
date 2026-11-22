"""Check the leading compact pair against Euclid FITS catalogues and external archives."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from astropy.coordinates import SkyCoord
from astropy.io import ascii

from catalogue import extract, stage

HERE = Path(__file__).resolve().parent
GAIA = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
SIMBAD = "https://simbad.cfa.harvard.edu/simbad/sim-tap/sync"
DESI = "https://datalab.noirlab.edu/tap/sync"


def read(url, path):
    with urlopen(url, timeout=25) as r:
        raw = r.read()
    path.write_bytes(raw)
    return raw


def catalogue(target, cache):
    t = {**target, "id": target["candidate"]}
    row = {}
    for kind in ("MER", "SPE", "PHZ", "PHZ_CLASS"):
        try:
            dest, file = stage(kind,t["tile"],cache)
            raw, _ = extract(dest, kind, t["tile"], [t], {t["id"]:row.get("MER",{}).get("rows",[])})
            row[kind] = {"file":file, "rows":raw[t["id"]]}
        except Exception as exc:
            row[kind] = {"error": str(exc)[:560]}
        print(t["id"], kind, len(row[kind].get("rows",[])), row[kind].get("error",""), flush=True)
    return row


def gaia(t, cache):
    query = GAIA+"?"+urlencode({"catalog":"gaia_dr3_source","objstr":f"{t['ra']} {t['dec']}",
                               "spatial":"cone","radius":5,"radunits":"arcsec","outfmt":1})
    raw = read(query,cache/"lead_gaia.tbl")
    table = ascii.read(raw.decode().splitlines(),format="ipac",guess=False)
    fields = ("source_id","ra","dec","ref_epoch","parallax","parallax_error",
              "pmra","pmdec","ruwe","phot_g_mean_mag")
    if not set(fields).issubset(table.colnames):
        raise ValueError("unexpected Gaia IPAC schema")
    return {"url":query,"sha256":hashlib.sha256(raw).hexdigest(),
            "rows":[{k:str(y[k]) for k in fields} for y in table]}


def simbad(t, cache):
    ra, dec = t["ra"], t["dec"]
    adql = ("SELECT TOP 30 main_id, otype, ra, dec, rvz_bibcode FROM basic "
            f"WHERE ra BETWEEN {ra-.003} AND {ra+.003} AND dec BETWEEN {dec-.002} AND {dec+.002}")
    query = SIMBAD+"?"+urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":adql})
    raw = read(query,cache/"lead_simbad.csv")
    rows = csv.DictReader(io.StringIO(raw.decode()))
    if not rows.fieldnames or "main_id" not in rows.fieldnames:
        raise ValueError("unexpected SIMBAD table schema")
    if len(results := list(rows)) == 30:
        raise ValueError("Catalogue query reached the row cap")
    sky = SkyCoord(ra,dec,unit="deg")
    near = []
    for r in results:
        sep = sky.separation(SkyCoord(float(r["ra"]),float(r["dec"]),unit="deg")).arcsec
        if sep<=5.:
            near.append({**r,"sep_arcsec":float(sep)})
    return {"url":query,"sha256":hashlib.sha256(raw).hexdigest(),"box_rows":len(results),"rows":near}


def desi(t, cache):
    ra, dec = t["ra"], t["dec"]
    adql = ("SELECT TOP 30 targetid, mean_fiber_ra, mean_fiber_dec, z, zerr, zwarn, spectype, zcat_primary "
            "FROM desi_dr1.zpix "
            f"WHERE mean_fiber_ra BETWEEN {ra-.003} AND {ra+.003} "
            f"AND mean_fiber_dec BETWEEN {dec-.002} AND {dec+.002}")
    query = DESI+"?"+urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":adql})
    raw = read(query,cache/"lead_desi.csv")
    rows = csv.DictReader(io.StringIO(raw.decode()))
    if not rows.fieldnames or "targetid" not in rows.fieldnames:
        raise ValueError("unexpected DESI table schema")
    if len(results := list(rows)) == 30:
        raise ValueError("Catalogue query reached the row cap")
    sky = SkyCoord(ra,dec,unit="deg")
    near = []
    for r in results:
        sep = sky.separation(SkyCoord(float(r["mean_fiber_ra"]),float(r["mean_fiber_dec"]),unit="deg")).arcsec
        if sep<=2.:
            near.append({**r,"sep_arcsec":float(sep)})
    return {"url":query,"sha256":hashlib.sha256(raw).hexdigest(),"box_rows":len(results),"rows":near}


def check(fn, target, cache):
    try:
        return fn(target, cache)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:500]}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache
    target = json.loads((cache/"selection.json").read_text())["candidates"][0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {fn.__name__: pool.submit(check,fn,target,cache) for fn in (catalogue,gaia,simbad,desi)}
        output = {k: f.result() for k,f in jobs.items()}
    (cache/"lead_catalogues.json").write_text(json.dumps({"candidate":target["candidate"],**output},
                                                         indent=2,allow_nan=False)+"\n")
    tables = output["catalogue"]
    if all("rows" in tables.get(k,{}) for k in ("MER","SPE")):
        cache.joinpath("spectrum").mkdir(exist_ok=True)
        spec = {"targets":{target["candidate"]:{k:tables[k]["rows"] for k in ("MER","SPE")}}}
        cache.joinpath("spectrum","euclid_catalogues.json").write_text(json.dumps(spec,allow_nan=False)+"\n")
