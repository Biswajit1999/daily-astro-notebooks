"""Record released VIS and NISP-J pixel flags at each audited peak."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from astropy.wcs import WCS
import numpy as np

from archive import BUCKET,fetch,get,header

R=Path("results")


def flags(row,band):
    tile=row["tile"]
    kind,n=("VIS","VIS") if band=="VIS" else ("NISP","NIR-J")
    prefix=f"dr1/MER/{tile}/{kind}/"
    doc=ET.fromstring(get(BUCKET+"/?"+urlencode({"list-type":2,"prefix":prefix})))
    found=[]
    for node in doc.findall(".//{*}Key"):
        file=node.text
        if f"-{n}-FLAG_" not in file: continue
        h,start,prov=header(f"{BUCKET}/{file}")
        if "-DATA_RELEASE_DEEP-" in h.get("PPLANID",""):
            found.append((h,start,prov))
    if len(found)!=1:
        raise ValueError("Missing or ambiguous deep flag mosaic")
    h,start,meta=found[0]
    if h["BITPIX"]!=32 or h.get("BZERO",0)!=0 or h.get("BSCALE",1)!=1:
        raise ValueError("Flag mosaic encoding differs from signed 32-bit")
    w=WCS(h).celestial
    x,y=w.world_to_pixel_values([row["ra1"],row["ra2"]],[row["dec1"],row["dec2"]])
    x,y=np.round(x).astype(int),np.round(y).astype(int)
    y0,y1=y.min()-3,y.max()+4
    n=h["NAXIS1"]
    lo,hi=int(start+y0*n*4),int(start+y1*n*4)
    raw,_,_=fetch(meta["url"],lo,hi,meta["etag"])
    img=np.frombuffer(raw,dtype=">i4").reshape(y1-y0,n)
    report=[]
    for xp,yp in zip(x,y-y0,strict=True):
        all_flags=img[yp-3:yp+4,xp-3:xp+4]
        report.append({"peak_flag":int(img[yp,xp]),"nonzero_7x7":int(np.count_nonzero(all_flags)),
                       "all_values":list(map(int,np.unique(all_flags)))})
    return {**meta,"byte_range":[lo,hi],"range_sha256":hashlib.sha256(raw).hexdigest(),"components":report}


def main():
    data=json.loads((R/"audit.json").read_text())
    jobs=[(name,r["candidate"],b) for name,r in data.items() for b in ("VIS","J")]
    def one(item):
        name,row,band=item
        try:
            d=flags(row,band)
        except Exception as e:
            d={"error":str(e)[:450]}
        return name,band,d
    out={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for name,b,d in pool.map(one,jobs): out.setdefault(name,{})[b]=d
    (R/"image_flags.json").write_text(json.dumps(out,indent=2)+"\n")


if __name__=="__main__":
    main()
