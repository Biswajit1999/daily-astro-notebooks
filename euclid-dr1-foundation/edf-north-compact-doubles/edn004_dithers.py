"""Check the EDN-004 1.316 µm feature in archived angular-orientation spectra."""
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path

from astropy.io import fits
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from archive import BUCKET,fetch,get
from spectra import line_check,REST
from vet import IRSA,tap

R=Path("results")
CACHE=Path("../cache")
IDS=(2718858072642847858,2718851317642848846)
CENTRE=REST["Halpha"]*(1+1.0040103197097778)


def read(key):
    url=f"{BUCKET}/{key.removeprefix('euclid/')}"
    local=CACHE/Path(key).name
    _,ss,etag=fetch(url,0,28800)
    if not local.exists():
        temp=local.with_suffix(".part")
        ranges=[(a,min(a+10_000_000,ss)) for a in range(0,ss,10_000_000)]
        with ThreadPoolExecutor(max_workers=4) as p,temp.open("wb") as f:
            for raw,s,e in p.map(lambda a:fetch(url,*a,etag=etag),ranges): f.write(raw)
        temp.replace(local)
    if ss!=local.stat().st_size:
        raise ValueError("Truncated SIR FITS")
    with local.open("rb") as handle:
        digest=hashlib.file_digest(handle,"sha256").hexdigest()
    return local,{"url":url,"etag":etag,"bytes":ss,"sha256":digest}


def inspect(hdu,centre):
    cols=hdu.columns.names
    if set(("WAVELENGTH","SIGNAL","VAR","MASK"))-set(cols):
        raise ValueError(f"Unexpected columns {cols}")
    if hdu.columns["WAVELENGTH"].unit.lower()!="angstrom":
        raise ValueError("Expected wavelengths in Angstrom")
    w,f,v,m=map(lambda k:np.asarray(hdu.data[k],float),("WAVELENGTH","SIGNAL","VAR","MASK"))
    finite=np.isfinite(w)&np.isfinite(f)&np.isfinite(v)&(v>0)
    q=finite&(m==0)
    check=line_check(w,f,v,q,centre)
    mask_core=finite&(np.abs(w-centre)<=32)
    val,n=np.unique(m[mask_core],return_counts=True)
    check["core_mask_counts"]={str(int(k)):int(i) for k,i in zip(val,n,strict=True)}
    core=q&(np.abs(w-centre)<30)
    altered=q.copy()
    if core.sum()>1:
        index=np.flatnonzero(core)
        altered[index[np.argmax((f/np.sqrt(np.maximum(v,1e-30)))[index])]]=False
        check["brightest_bin_removed"]=line_check(w,f,v,altered,centre)
    return check,(w,f,v,q,finite)


def main():
    q=f"SELECT * FROM euclid.objectid_spectrafile_association_dr1 WHERE objectid IN ({IDS[0]},{IDS[1]})"
    path=R/"edn004_sir_association.csv"
    if not path.exists():
        n,res=tap("edn004_sir_association",IRSA,q,R,100)
        if "error" in res: raise ValueError(res["error"])
    with path.open() as f:
        direct=list(csv.DictReader(f))
    rel={}
    for item in direct:
        rel.setdefault(item["path"],[]).append(int(item["objectid"]))
    report={"query":{"endpoint":IRSA,"adql":q},"line_wavelength_A":CENTRE,
            "single_line_redshift_alternatives":{x:CENTRE/w-1 for x,w in REST.items() if x in ("Halpha","[O III]","[O II]")},
            "sources":[],"fits":[]}
    traces=[]
    for key,ids in rel.items():
        try:
            f,meta=read(key)
            report["sources"].append(meta)
            with fits.open(f,memmap=True) as h:
                grism=h[0].header["LRANGE"]
                for obj in ids:
                    members=[x.name.split("_")[0] for x in h if x.name.endswith("_META") and x.header.get("OBJ_ID")==obj]
                    if len(members)!=1: raise ValueError(f"{obj}: expected one identity HDU")
                    prefix=members[0]
                    for x in h:
                        if not x.name.startswith(prefix+"_") or not x.name.endswith("_SIGNAL"):
                            continue
                        r,d=inspect(x,CENTRE)
                        cont=x.name.removesuffix("_SIGNAL")+"_CONTAMINANTS"
                        near_ids=list(map(int,np.unique(h[cont].data["OBJ_ID"]))) if cont in h else None
                        entry={"object_id":obj,"grism":grism,"hdu":x.name,"gwa_pos":x.header.get("GWA_POS"),
                               "gwa_tilt":x.header.get("GWA_TILT"),"contaminants":near_ids,**r}
                        report["fits"].append(entry)
                        if obj==IDS[0] and "_COMBINED" in x.name:
                            traces.append((grism,d))
        except Exception as e:
            report["sources"].append({"key":key,"error":str(e)[:450]})
    (R/"edn004_dithers.json").write_text(json.dumps(report,indent=2)+"\n")
    fig,axes=plt.subplots(1,2,figsize=(8.4,3.3),sharex=True,sharey=True,layout="constrained")
    for ax,(grism,(w,f,v,good,valid)) in zip(axes,traces):
        use=valid&(abs(w-CENTRE)<150)
        clean=use&good
        ax.plot((w[use]-CENTRE),f[use]/np.sqrt(v[use]),color=".55",lw=.8)
        ax.scatter(w[clean]-CENTRE,f[clean]/np.sqrt(v[clean]),s=13,c="#216d7a",label="Mask = 0")
        ax.axvline(0,color="#a33d55",ls="--",lw=1)
        ax.set(title=grism,xlabel="Wavelength from 13155.55 Å (Å)")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("Signal / formal σ per bin")
    fig.suptitle("EDN-004 · one candidate line, two Euclid grisms")
    fig.savefig(R/"edn004_line.png",dpi=155)
    print(len(report["fits"]),report["sources"],flush=True)


if __name__=="__main__":
    main()
