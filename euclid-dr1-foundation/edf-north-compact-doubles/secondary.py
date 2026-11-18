"""Crossmatch the ECLIPSE public object catalogue and look for independent spectra."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

from astropy.coordinates import SkyCoord
import astropy.units as u

from archive import get
from vet import cone,tap

ECLIPSE="https://zenodo.org/records/19654904/files/ECLIPSE_object_catalogue.zip?download=1"
DESI="https://datalab.noirlab.edu/tap/sync"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results",type=Path,default=Path("results"))
    p.add_argument("--catalogue",type=Path,required=True)
    args=p.parse_args()
    if not args.catalogue.exists(): args.catalogue.write_bytes(get(ECLIPSE,45))
    raw=args.catalogue.read_bytes()
    if hashlib.md5(raw).hexdigest()!="56433fecbdc459046ffe9eca44bb4dcf":
        raise ValueError("Published ECLIPSE MD5 mismatch")
    with ZipFile(io.BytesIO(raw)) as z:
        archive=list(csv.DictReader(io.StringIO(z.read("ECLIPSE_object_catalogue/ECLIPSE_object_catalogue.csv").decode())))
    if len(archive)!=26662:
        raise ValueError("Unexpected ECLIPSE row count")
    with (args.results/"candidates.csv").open() as f:
        targets=[r for r in csv.DictReader(f) if r["j_state"]=="pass"]
    sky=SkyCoord([float(r["ra"]) for r in targets],[float(r["dec"]) for r in targets],unit="deg")
    lits=SkyCoord([float(r["RA_obj"]) for r in archive],[float(r["DEC_obj"]) for r in archive],unit="deg")
    match,sep,_=sky.match_to_catalog_sky(lits)
    result=[]
    for r,i,d in zip(targets,match,sep.arcsec,strict=True):
        l=archive[i]
        result.append({"candidate":r["id"],"ra":r["ra"],"dec":r["dec"],
                       "nearest_eclipse_arcsec":float(d),"within_3arcsec":bool(d<=3),
                       "eclipse_id":l["Unique_Identifier"],"grade":l["Expert_Grade"],
                       "earliest_publication":l["earliest_publication_bibcode"]})
    with (args.results/"eclipse_crossmatch.csv").open("w") as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]))
        w.writeheader()
        w.writerows(result)
    terms=[cone(float(s["ra"]),float(s["dec"]),2,"mean_fiber_ra","mean_fiber_dec") for s in targets[:6]]
    query=("SELECT TOP 500 targetid,mean_fiber_ra,mean_fiber_dec,z,zerr,zwarn,spectype,zcat_primary "
           f"FROM desi_dr1.zpix WHERE ({' OR '.join(terms)})")
    _,desi=tap("desi_dr1",DESI,query,args.results,500)
    (args.results/"secondary_checks.json").write_text(json.dumps(
        {"eclipse":{"url":ECLIPSE,"sha256":hashlib.sha256(raw).hexdigest(),"rows":len(archive),
                    "n_euclid_repeaters":len(targets),"within_3arcsec":[r for r in result if r["within_3arcsec"]],
                    "top6_nearest":result[:6]},"desi":desi},indent=2)+"\n")


if __name__=="__main__":
    main()
