"""Crossmatch the audited image peaks with official DR1-F per-tile FITS tables."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from astropy.coordinates import SkyCoord
from astropy.io import fits
import numpy as np

from archive import BUCKET,fetch,get

TABLES={"MER":("MER_FINAL_CATALOG","_FINAL-CAT_"),
        "PHZ":("PHZ_DEEP_OUTPUT_CATALOG","_PHZCAT_"),
        "SPE":("SPE_PF_OUTPUT_CATALOG","_DEEP-CAT-Z-"),
        "PHZ_CLASS":("PHZ_DEEP_OUTPUT_CATALOG","_CLASSCAT_")}
KEEP={
 "MER":("OBJECT_ID","RA","DEC","RIGHT_ASCENSION","DECLINATION","RA_CENTROID","DEC_CENTROID",
        "TILE_INDEX","VIS_DET","DET_QUALITY_FLAG","FLAG_VIS","FLAG_J","PARENT_ID","ELLIPTICITY",
        "DEBLENDED_FLAG","PARENT_VISNIR","POINT_LIKE_PROB","POINT_LIKE_FLAG",
        "FLUX_VIS_2FWHM_APER","FLUXERR_VIS_2FWHM_APER","FLUX_Y_2FWHM_APER","FLUXERR_Y_2FWHM_APER",
        "FLUX_J_2FWHM_APER","FLUXERR_J_2FWHM_APER","FLUX_H_2FWHM_APER","FLUXERR_H_2FWHM_APER",
        "FLUX_G_EXT_HSC_2FWHM_APER","FLUXERR_G_EXT_HSC_2FWHM_APER",
        "FLUX_Z_EXT_HSC_2FWHM_APER","FLUXERR_Z_EXT_HSC_2FWHM_APER"),
 "PHZ":("OBJECT_ID","PHZ_MEDIAN","PHZ_70_INT_1","PHZ_70_INT_2","PHZ_90_INT_1","PHZ_90_INT_2","PHZ_70_INT","PHZ_90_INT", "PHZ_MODE_1_AREA","PHZ_MODE_2_AREA",
        "PHZ_MODE_1","PHZ_MODE_2","PHZ_FLAGS","PHZ_CLASSIFICATION"),
 "PHZ_CLASS":("OBJECT_ID","PHZ_CLASSIFICATION","PHZ_STAR_PROB","PHZ_GAL_PROB","PHZ_QSO_PROB"),
 "SPE":("OBJECT_ID","SPE_Z","SPE_Z_ERR","SPE_Z_PROB","SPE_Z_REL","SPE_RANK","SPE_CLASS","SPE_QUALITY_FLAG",
        "SPE_DZH","SPE_DZL","SPE_FLAGS","SPE_ERROR_FLAG","SPE_WARNING_FLAG",
        "SPE_GAL_ERROR_FLAG","SPE_GAL_WARNING_FLAG","SPE_W_MIN","SPE_W_MAX","SPE_GRISM",
        "SPE_Z_REDUCED_CHI2","SPE_CONT_SNR")
}


def stage(kind,tile,cache):
    directory,token=TABLES[kind]
    prefix=f"dr1/catalogs/{directory}/{tile}/"
    data=get(f"{BUCKET}/?"+urlencode({"list-type":2,"prefix":prefix}))
    root=ET.fromstring(data)
    choices=[e for e in root.findall(".//{*}Contents") if token in e.findtext("{*}Key","")]
    if len(choices)!=1:
        raise ValueError(f"{kind} {tile}: expected one FITS table, got {len(choices)}")
    key=choices[0].findtext("{*}Key")
    size=int(choices[0].findtext("{*}Size"))
    url=f"{BUCKET}/{key}"
    dest=cache/Path(key).name
    head,total,etag=fetch(url,0,28800)
    if total!=size:
        raise ValueError("FITS size mismatch")
    marker=dest.with_suffix(".etag")
    if not (dest.is_file() and dest.stat().st_size==size and marker.is_file() and marker.read_text()==etag):
        temp=dest.with_suffix(".part")
        spans=[(i,min(i+12_000_000,size)) for i in range(0,size,12_000_000)]
        with ThreadPoolExecutor(max_workers=3) as w, temp.open("wb") as stream:
            for part,_,_ in w.map(lambda p:fetch(url,*p,etag=etag),spans):
                stream.write(part)
        temp.replace(dest)
        marker.write_text(etag)
    with dest.open("rb") as f:
        digest=hashlib.file_digest(f,"sha256").hexdigest()
    return dest, {"url":url,"etag":etag,"bytes":size,"sha256":digest,"kind":kind,"tile":tile}


def scalar(x):
    if isinstance(x,np.generic): x=x.item()
    if isinstance(x,bytes): return x.decode(errors="replace").strip()
    if isinstance(x,float) and not np.isfinite(x): return None
    if isinstance(x,np.ndarray): return [scalar(y) for y in x]
    return x


def extract(path,kind,tile,targets,ids):
    answer={}
    seen=[]
    with fits.open(path,memmap=True) as f:
        for h in f:
            if not isinstance(h,fits.BinTableHDU) or "OBJECT_ID" not in h.columns.names:
                continue
            names=h.columns.names
            seen.append({"hdu":h.name,"rows":len(h.data),"columns":names})
            keep=[k for k in KEEP[kind] if k in names]
            if kind=="MER":
                x,y=next((x,y) for x,y in (("RIGHT_ASCENSION","DECLINATION"),("RA","DEC"),("RA_CENTROID","DEC_CENTROID")) if x in names and y in names)
                a,b=np.asarray(h.data[x],float),np.asarray(h.data[y],float)
                valid=np.flatnonzero(np.isfinite(a)&np.isfinite(b)&(abs(b)<=90))
                fits_pos=SkyCoord(a[valid],b[valid],unit="deg")
                for r in targets:
                    distance=SkyCoord(float(r["ra"]),float(r["dec"]),unit="deg").separation(fits_pos).arcsec
                    rows=valid[distance<=1.4]
                    peaks=SkyCoord([float(r["ra1"]),float(r["ra2"])],[float(r["dec1"]),float(r["dec2"])],unit="deg")
                    matches=[]
                    for i in rows:
                        s=SkyCoord(a[i],b[i],unit="deg")
                        record={k:scalar(h.data[k][i]) for k in keep}
                        record.update(ra_deg=a[i],dec_deg=b[i],peak_offsets_arcsec=peaks.separation(s).arcsec.tolist())
                        matches.append(record)
                    answer[r["id"]]=matches
            else:
                for r in targets:
                    available=[m["OBJECT_ID"] for m in ids[r["id"]]]
                    include=np.flatnonzero(np.isin(h.data["OBJECT_ID"],available))
                    answer.setdefault(r["id"],[]).extend(
                        {"hdu":h.name,**{k:scalar(h.data[k][i]) for k in keep}} for i in include)
    return answer,seen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache",type=Path,required=True)
    p.add_argument("--results",type=Path,default=Path("results"))
    a=p.parse_args()
    with (a.results/"candidates.csv").open() as f:
        rows=[r for r in csv.DictReader(f) if r["j_state"]=="pass"][:6]
    by_tile={tile:[r for r in rows if int(r["tile"])==tile] for tile in sorted({int(r["tile"]) for r in rows})}
    record={"files":[],"targets":{r["id"]: {} for r in rows}}
    def one(entry):
        kind,tile=entry
        try:
            dest,provenance=stage(kind,tile,a.cache)
            available={r["id"]:record["targets"][r["id"]].get("MER",[]) for r in by_tile[tile]}
            matches,hdu=extract(dest,kind,tile,by_tile[tile],available)
            return kind,{**provenance,"hdu":hdu},matches
        except Exception as e:
            return kind,{"tile":tile,"kind":kind,"error":str(e)},{}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for kinds in (["MER"],["PHZ","SPE","PHZ_CLASS"]):
            for kind,provenance,rows in pool.map(one,[(k,t) for k in kinds for t in by_tile]):
                print(kind,provenance["tile"],{i:len(x) for i,x in rows.items()},provenance.get("error",""),flush=True)
                record["files"].append(provenance)
                for target,matched in rows.items():
                    record["targets"][target][kind]=matched
    (a.results/"euclid_catalogues.json").write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
