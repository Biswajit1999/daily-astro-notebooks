"""Retrieve exact-object DR1-F NISP spectra and perform fixed-window line fits."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct

from astropy import units as u
from astropy_healpix import HEALPix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from archive import BUCKET,fetch,get
from line_fits import line_check

BASE=(f"{BUCKET}/contributed/dr1/hats/reformatted_catalogs/sir_combined_spectra/"
      "euclid_dr1_reformatted_catalogs_sir_combined_spectra-hats")
REST={"[O II]":3727.42,"Hbeta":4862.68,"[O III]":5008.24,"Halpha":6564.61,"[S II]":6718.29}
COLUMNS=["object_id","tileid","lrange","n_dith","spectrum"]


def lookup(catalogues,cache):
    raw=get(f"{BASE}/partition_info.csv")
    parts=[]
    matches={}
    expected={}
    for ident,values in catalogues["targets"].items():
        for m in values.get("MER",[]):
            i=m["OBJECT_ID"]
            matches[i]=ident
            expected[i]=(m["ra_deg"],m["dec_deg"],m["TILE_INDEX"])
    by_nside={}
    for r in csv.DictReader(io.StringIO(raw.decode())):
        n=int(r["Norder"])
        if n not in by_nside:
            h=HEALPix(nside=2**n,order="nested")
            by_nside[n]=set().union(*(h.cone_search_lonlat(a*u.deg,b*u.deg,8*u.arcsec) for a,b,t in expected.values()))
        if int(r["Npix"]) in by_nside[n]:
            path=f"Norder={n}/Dir={r['Dir']}/Npix={r['Npix']}/part0.snappy.parquet"
            parts.append((f"{BASE}/dataset/{path}",int(r["num_rows"])))
    ids=pa.array(list(matches),type=pa.int64())

    def one(p):
        url,nrows=p
        try:
            return read_part(url,nrows,ids,cache)
        except Exception as e:
            return [],{"url":url,"error":str(e)[:500]}

    data=[]
    provenance=[]
    with ThreadPoolExecutor(max_workers=4) as workers:
        for spectra,manifest in workers.map(one,parts):
            provenance.append(manifest)
            for rec in spectra:
                ident=rec["object_id"]
                rec["target"]=matches[ident]
                rec["tile_matches"]=expected[ident][2]==rec["tileid"]
                data.append(rec)
    return data,{"partition_index_url":f"{BASE}/partition_info.csv",
                 "index_sha256":hashlib.sha256(raw).hexdigest(),"sources":provenance}


def read_part(url,nrows,ids,cache):
    prefix=hashlib.sha256(url.encode()).hexdigest()[:16]
    # S3 publishes file size in Content-Range; a first range also pins the ETag.
    _,size,tag=fetch(url,0,4)
    tail,_,_=fetch(url,size-8,size,tag)
    l,magic=struct.unpack("<I4s",tail)
    if magic!=b"PAR1" or not 0<l<10_000_000:
        raise ValueError("Invalid Parquet footer")
    hstart=size-8-l
    footer,_,_=fetch(url,hstart,size,tag)
    m=pq.read_metadata(pa.BufferReader(b"PAR1"+footer))
    if m.num_rows!=nrows:
        raise ValueError("Partition count mismatch")
    path=cache/f"spec-{prefix}.parquet"
    ranges=[]
    with path.open("wb") as f:
        f.write(b"PAR1")
        f.seek(hstart)
        f.write(footer)
    ranges.append([hstart,size,hashlib.sha256(footer).hexdigest()])

    def get_chunk(c):
        start=c.dictionary_page_offset or c.data_page_offset
        stop=start+c.total_compressed_size
        a,_,_=fetch(url,start,stop,tag)
        return start,stop,a

    def fill(tasks):
        with path.open("r+b") as f,ThreadPoolExecutor(max_workers=6) as workers:
            for a,b,data in workers.map(get_chunk,tasks):
                f.seek(a); f.write(data)
                ranges.append([a,b,hashlib.sha256(data).hexdigest()])

    def group_columns(i, cols):
        g=m.row_group(i)
        return [g.column(j) for j in range(g.num_columns) if g.column(j).path_in_schema.split(".")[0] in cols]
    fill([c for i in range(m.num_row_groups) for c in group_columns(i,["object_id"])])
    result=[]
    for i in range(m.num_row_groups):
        table=pq.ParquetFile(path,memory_map=True)
        col=table.read_row_group(i,columns=["object_id"])["object_id"]
        ind=pc.indices_nonzero(pc.is_in(col,value_set=ids))
        if not len(ind):
            continue
        fill(group_columns(i,COLUMNS[1:]))
        table=pq.ParquetFile(path,memory_map=True)
        result.extend(table.read_row_group(i,columns=COLUMNS).take(ind).to_pylist())
    return result,{"url":url,"etag":tag,"rows":nrows,"ranges":ranges,"exact_id_matches":len(result)}


def as_array(d,name):
    return np.asarray(d[name],dtype=float)


def scientific_checks(spectra,catalogue,out):
    report=[]
    plots={}
    for s in spectra:
        if not s["tile_matches"]: continue
        d=s["spectrum"]; s_id=s["object_id"]
        w,f,v,m=(as_array(d,k) for k in ("wavelength","signal","var","mask"))
        quality=np.isfinite(w)&np.isfinite(f)&np.isfinite(v)&(v>0)
        clean=quality&(m==0)
        if not clean.any():
            report.append({"id":s["target"],"object_id":s_id,"grism":s["lrange"],"state":"no_clean_bins"})
            continue
        if not 8500<np.median(w[clean])<22000:
            raise ValueError("Expected SIR wavelength in Angstrom")
        rows=catalogue["targets"][s["target"]].get("SPE",[])
        model=next((r for r in rows if r["OBJECT_ID"]==s_id and r["hdu"]=="SPE_GALAXY_CANDIDATES" and r.get("SPE_RANK")==0),{})
        z=model.get("SPE_Z")
        lines={name:line_check(w,f,v,clean,rest*(1+z)) for name,rest in REST.items()} if z is not None else {}
        report.append({"id":s["target"],"object_id":s_id,"grism":s["lrange"],"n_dith":s["n_dith"],
                       "clean_bins":int(clean.sum()),"finite_bins":int(quality.sum()),"wavelength_range_A":[float(min(w[clean])),float(max(w[clean]))],
                       "clean_peak_bin_snr":float(np.max(f[clean]/np.sqrt(v[clean]))),
                       "SPE_z":z,"fixed_windows":lines})
        if s["target"] in ("EDN-002","EDN-003","EDN-004"):
            plots.setdefault(s["target"],{}).setdefault(s_id,[]).append((s["lrange"],w,f,v,quality,clean,z,lines))
    for name, objects in plots.items():
        fig,axs=plt.subplots(len(objects),1,figsize=(8.5,2.1*len(objects)+.5),sharex=True,layout="constrained",squeeze=False)
        for (i, items),ax in zip(objects.items(),axs.ravel(),strict=True):
            for grism,w,f,v,q,c,z,lines in items:
                ax.plot(w[q]/1e4,f[q]/np.sqrt(v[q]),color=".7",alpha=.4,lw=.45)
                ax.scatter(w[c]/1e4,f[c]/np.sqrt(v[c]),s=3,label=grism)
                for label,line in lines.items():
                    if line.get("snr",0)>=4:
                        ax.axvline(line["center_A"]/1e4,color="#873f61",lw=.8,ls="--")
                        ax.text(line["center_A"]/1e4,.97,label,transform=ax.get_xaxis_transform(),va="top",fontsize=7)
            ax.set(title=str(i),ylabel="Signal / σ per bin")
            ax.axhline(0,color=".3",lw=.4)
            ax.legend(loc="upper right",fontsize=7)
        axs[-1,0].set_xlabel("Observed vacuum wavelength (µm)")
        fig.savefig(out/"audit"/name/"spectra.png",dpi=145)
        plt.close(fig)
    return report


def safe(x):
    if isinstance(x,float) and not np.isfinite(x): return None
    if isinstance(x,list): return [safe(i) for i in x]
    if isinstance(x,dict): return {k:safe(v) for k,v in x.items()}
    return x


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache",type=Path,required=True)
    p.add_argument("--results",type=Path,default=Path("results"))
    a=p.parse_args()
    c=json.loads((a.results/"euclid_catalogues.json").read_text())
    data,manifest=lookup(c,a.cache)
    manifest["checks"]=scientific_checks(data,c,a.results)
    (a.results/"nisp_spectra.json.gz").write_bytes(gzip.compress(
        json.dumps(safe(data),allow_nan=False,separators=(",",":")).encode(),mtime=0))
    (a.results/"spectral_checks.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n")
    print(len(data),"SIR rows",len(manifest["sources"]),"partitions",flush=True)


if __name__=="__main__":
    main()
