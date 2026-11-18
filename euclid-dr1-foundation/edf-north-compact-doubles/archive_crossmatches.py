"""Resolve public archive comparisons via working public mirrors."""
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlencode

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import ascii
from matplotlib.path import Path as Polygon
import numpy as np

from archive import get
from vet import cone,tap,MAST

R=Path("results")
DS="https://datalab.noirlab.edu/tap/sync"
GA="https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
SIM="https://simbad.cfa.harvard.edu/simbad/sim-tap/sync"
WDS="https://www.astro.gsu.edu/wds/Webtextfiles/wds_precise.txt"


def matched(r,rows,x,y,maxsep):
    p=SkyCoord(float(r["ra"]),float(r["dec"]),unit="deg")
    return [{**d,"offset_arcsec":float(s.arcsec)} for d in rows if d[x] and d[y]
            if (s:=p.separation(SkyCoord(float(d[x]),float(d[y]),unit="deg"))) <=maxsep*u.arcsec]


def wds_data():
    raw=get(WDS,40)
    out=[]
    for s in raw.decode("ascii",errors="replace").splitlines():
        m=re.search(r"(?<!\d)([012]\d[0-5]\d[0-5]\d\.\d\d)([+-]\d\d[0-5]\d[0-5]\d\.\d)(?:\s|$)",s)
        if m:
            a,b=m.groups()
            ra=15*(int(a[:2])+int(a[2:4])/60+float(a[4:])/3600)
            dec=(1 if b[0]=="+" else -1)*(int(b[1:3])+int(b[3:5])/60+float(b[5:])/3600)
            out.append((ra,dec,s[:10],s[10:17]))
    if len(out)<60_000:
        raise ValueError(f"Parsed only {len(out)} WDS rows, check the file layout")
    return out,hashlib.sha256(raw).hexdigest()


def main():
    with (R/"candidates.csv").open() as f:
        targets=list(csv.DictReader(f))[:6]
    a=np.asarray([float(x["ra"]) for x in targets])
    b=np.asarray([float(x["dec"]) for x in targets])
    pts=SkyCoord(a,b,unit="deg")
    p=(a.min()-.35,a.max()+.35,b.min()-.24,b.max()+.24)
    query=(f"SELECT TOP 10000 obs_collection,obs_id,instrument_name,s_ra,s_dec,s_region,access_url "
           "FROM ivoa.obscore WHERE obs_collection IN ('HST','JWST') AND dataproduct_type='image' "
           f"AND s_ra BETWEEN {p[0]} AND {p[1]} AND s_dec BETWEEN {p[2]} AND {p[3]}")
    desi=(f"SELECT TOP 10000 targetid,mean_fiber_ra,mean_fiber_dec,z,zerr,zwarn,spectype,zcat_primary "
          f"FROM desi_dr1.zpix WHERE mean_fiber_ra BETWEEN {p[0]} AND {p[1]} "
          f"AND mean_fiber_dec BETWEEN {p[2]} AND {p[3]}")
    with ThreadPoolExecutor(max_workers=3) as pool:
        f1=pool.submit(tap,"mast_box",MAST,query,R,10000)
        f2=pool.submit(tap,"desi_box",DS,desi,R,10000)
        f3=pool.submit(wds_data)
        mast,desi=f1.result()[1],f2.result()[1]
        try:
            wds,sha=f3.result()
            wdsc=SkyCoord([r[0] for r in wds],[r[1] for r in wds],unit="deg")
            index,sep,_=pts.match_to_catalog_sky(wdsc)
            wdsm={t["id"]:{"nearest_sep_arcsec":float(s.arcsec),"id":wds[i][2],"designation":wds[i][3],
                           "within_15arcsec":bool(s.arcsec<=15)} for t,i,s in zip(targets,index,sep,strict=True)}
            wd={"url":WDS,"parsed_rows":len(wds),"sha256":sha,"targets":wdsm}
        except Exception as e:
            wd={"url":WDS,"error":str(e)[:650]}
    mast_targets={r["id"]:[] for r in targets}
    unsupported=0
    for record in mast.pop("data",[]):
        tokens=record["s_region"].split()
        tokens=[x for x in tokens if x!="ICRS"]
        if not tokens or tokens[0]!="POLYGON":
            unsupported+=1
            continue
        val=np.asarray(tokens[1:],dtype=float).reshape(-1,2)
        for r in targets:
            if Polygon(val).contains_point([float(r["ra"]),float(r["dec"])]):
                mast_targets[r["id"]].append({"obs_id":record["obs_id"],"instrument":record["instrument_name"],
                                              "collection":record["obs_collection"],"url":record["access_url"]})
    mast.update(containing_target=mast_targets,unsupported_footprints=unsupported)
    dr=desi.pop("data",[])
    desi["targets"]={r["id"]:matched(r,dr,"mean_fiber_ra","mean_fiber_dec",2) for r in targets}

    def one(r):
        d=R/"audit"/r["id"]
        url=GA+"?"+urlencode({"catalog":"gaia_dr3_source","objstr":f'{r["ra"]} {r["dec"]}',
                             "spatial":"cone","radius":10,"radunits":"arcsec","outfmt":1})
        gaia={"url":url}
        try:
            raw=get(url,23)
            res=ascii.read(raw.decode().splitlines(),format="ipac",guess=False)
            if "source_id" not in res.colnames:
                raise ValueError("Unexpected Gaia mirror format")
            (d/"gaia_dr3_irsa.tbl").write_bytes(raw)
            fields=("source_id","ra","dec","ref_epoch","parallax","parallax_error","pmra","pmdec","ruwe","phot_g_mean_mag","dist")
            gaia.update(rows=len(res),matches=[{k:str(y[k]) for k in fields if k in res.colnames} for y in res],
                        sha256=hashlib.sha256(raw).hexdigest())
        except Exception as e:
            gaia["error"]=str(e)[:350]
        here=cone(r["ra"],r["dec"],6)
        query=f"SELECT TOP 100 main_id,otype,ra,dec,rvz_redshift,rvz_bibcode FROM basic WHERE {here}"
        _,sim=tap("simbad_mirror",SIM,query,d,100)
        return r["id"],{"gaia_irsa":gaia,"simbad":sim}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=dict(pool.map(one,targets))
    report={"gaia_simbad":rows,"wds":wd,"mast":mast,"desi":desi}
    (R/"public_archive_crossmatches.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    main()
