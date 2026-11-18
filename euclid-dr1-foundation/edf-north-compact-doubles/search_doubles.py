"""Classical detection of compact optical pairs and fixed-position NISP checks."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
import io
import json
import math
from pathlib import Path

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
import numpy as np
from scipy.ndimage import distance_transform_cdt, gaussian_filter, map_coordinates, maximum_filter
from scipy.spatial import cKDTree

from archive import TILES, WIDTH, image_strip

EDGE=16


def robust(samples):
    median = float(np.median(samples))
    return median, float(1.4826*np.median(np.abs(samples-median)))


def dog(data, small, large):
    good=np.isfinite(data) & (data!=0)
    sane=np.where(good,data,0).astype(np.float32,copy=False)
    return gaussian_filter(sane,small)-gaussian_filter(sane,large),good


def segment_dip(image, a, b, baseline):
    frac=np.linspace(.15,.85,15)
    coords=np.array(a)[:,None]+(np.array(b)-a)[:,None]*frac
    faint=min(float(image[tuple(a)]),float(image[tuple(b)]))-baseline
    if faint<=0:
        return 0.
    values=map_coordinates(image,coords,order=1,prefilter=False)
    return float((faint-(values.min()-baseline))/faint)


def detect(filtered, good, sign, header, origin, tile):
    img=filtered*sign
    maskdist=distance_transform_cdt(good,metric="chessboard")
    maskdist[maskdist<0]=np.iinfo(maskdist.dtype).max
    score=np.full(img.shape, np.nan,dtype=np.float32)
    means=np.zeros((12,12))
    for y in range(12):
        for x in range(12):
            sl=(slice(512*y,512*(y+1)),slice(512*x,512*(x+1)))
            cell=img[sl][maskdist[sl]>14]
            if len(cell)<1000:
                continue
            centre,sigma=robust(cell)
            if sigma>0:
                score[sl]=(img[sl]-centre)/sigma
                means[y,x]=centre
    yy,xx=np.nonzero((score>=6)&(img==maximum_filter(img,size=5)))
    points=np.column_stack((yy,xx))
    tree=cKDTree(points)
    peaks=score[yy,xx]
    bright=points[peaks>1000]
    halo=cKDTree(bright)
    pairs=tree.query_pairs(9.5,output_type="ndarray")
    records=[]
    for p,q in pairs:
        a,b=points[p],points[q]
        if sum((a-b)**2)<3.8**2 or max(peaks[p],peaks[q])<8:
            continue
        if img[tuple(b)]>img[tuple(a)]:
            a,b,p,q=b,a,q,p
        y,x=a
        base=means[y//512,x//512]
        w=(float(img[tuple(a)])-base,float(img[tuple(b)])-base)
        ratio=w[1]/w[0] if w[0]>0 else 0
        midpoint=(a+b)/2
        dip=segment_dip(img,a,b,base)
        flags=[]
        if ratio<.25: flags.append("flux_ratio")
        if dip<.15: flags.append("saddle")
        if min(maskdist[tuple(a)],maskdist[tuple(b)])<=14: flags.append("invalid_or_zero")
        if np.any(a<EDGE) or np.any(b<EDGE) or np.any(a>=WIDTH-EDGE) or np.any(b>=WIDTH-EDGE):
            flags.append("border")
        if len(halo.query_ball_point(midpoint,70)) or len(halo.query_ball_point(a,70)) or len(halo.query_ball_point(b,70)):
            flags.append("bright_peak")
        if len(tree.query_ball_point(midpoint,15))>2: flags.append("third_peak")
        records.append({"tile":tile,"sign":sign,"vis_y1":int(a[0]),"vis_x1":int(a[1]),
                        "vis_y2":int(b[0]),"vis_x2":int(b[1]),"vis_score1":float(peaks[p]),
                        "vis_score2":float(peaks[q]),"vis_peak_ratio":float(ratio),"vis_dip":dip,
                        "flags":";".join(flags)})
    wcs=WCS(header).celestial
    x0,y0=origin
    if records:
        p=wcs.pixel_to_world(np.array([r["vis_x1"] for r in records])+x0,
                             np.array([r["vis_y1"] for r in records])+y0)
        q=wcs.pixel_to_world(np.array([r["vis_x2"] for r in records])+x0,
                             np.array([r["vis_y2"] for r in records])+y0)
        pa,sep=p.position_angle(q),p.separation(q)
        mid=p.directional_offset_by(pa,sep/2)
        keys=("ra1","dec1","ra2","dec2","ra","dec","sep_arcsec","pa_deg")
        for r,values in zip(records,zip(p.ra.deg,p.dec.deg,q.ra.deg,q.dec.deg,
                                         mid.ra.deg,mid.dec.deg,sep.arcsec,pa.deg),strict=True):
            r.update(zip(keys,map(float,values),strict=True))
    return records,len(points)


def run_vis(tile,cache):
    try:
        data,header,meta=image_strip(tile,"VIS",cache)
        wcs=WCS(header).celestial
        origin=meta["origin_xy"]
        p=wcs.pixel_to_world(WIDTH/2+origin[0],WIDTH/2+origin[1])
        image,good=dog(data,.85,3.)
        records=[]
        counts={}
        for sign in (1,-1):
            rec,n=detect(image,good,sign,header,origin,tile)
            records.extend(rec)
            counts[str(sign)]={"peaks":n,"pairs":len(rec),"accepted":sum(not r["flags"] for r in rec)}
        active=int(good[EDGE:-EDGE,EDGE:-EDGE].sum())
        return {"tile":tile,"vis":meta,"ra":float(p.ra.deg),"dec":float(p.dec.deg),
                "active_vis_pixels":active,"counts":counts},records
    except Exception as exc:
        return {"tile":tile,"vis_error":f"{type(exc).__name__}: {exc}"},[]


def j_check(jmap, good, pos):
    xx,yy=pos
    x,y=round(float(np.mean(xx))),round(float(np.mean(yy)))
    half=67
    if not (half <= y < jmap.shape[0] - half and half <= x < jmap.shape[1] - half):
        return {"state":"border"}
    cut=jmap[y-half:y+half+1,x-half:x+half+1]
    usable=good[y-half:y+half+1,x-half:x+half+1]
    grid=np.arange(-half,half+1)
    distance=np.hypot(grid[:,None],grid)
    ann=(distance>=20)&(distance<=65)&usable
    if ann.sum()<.9*((distance>=20)&(distance<=65)).sum():
        return {"state":"coverage"}
    centre,sigma=robust(cut[ann])
    if not np.isfinite(sigma) or sigma<=0:
        return {"state":"noise"}
    best=[]
    for xp,yp in zip(xx-x+half,yy-y+half,strict=True):
        ix,iy=round(xp),round(yp)
        if not usable[iy-3:iy+4,ix-3:ix+4].all():
            return {"state":"coverage"}
        a,b=np.mgrid[iy-3:iy+4,ix-3:ix+4]
        in_tolerance=np.hypot(a-yp,b-xp)<=1.6
        peaks=cut[iy-3:iy+4,ix-3:ix+4]
        local_max=maximum_filter(peaks,size=3)
        vals=np.where(in_tolerance&(peaks==local_max),peaks,-np.inf)
        k=np.unravel_index(vals.argmax(),vals.shape)
        if not np.isfinite(vals[k]):
            return {"state":"no_local_peak","noise":sigma}
        best.append((int(a[k]),int(b[k])))
    a,b=best
    scores=[float((cut[z]-centre)/sigma) for z in best]
    dip=segment_dip(cut,a,b,centre)
    sep=float(np.linalg.norm(np.subtract(a,b))*.1)
    state="pass" if min(scores)>=4 and sep>=.25 and dip>=.10 else "no_repeat"
    return {"state":state,"score1":scores[0],"score2":scores[1],"sep_arcsec":sep,"dip":dip,
            "noise":sigma,"x1":a[1]+x-half,"y1":a[0]+y-half,
            "x2":b[1]+x-half,"y2":b[0]+y-half}


def run_j(tile,cache,records):
    try:
        data,header,meta=image_strip(tile,"J",cache)
        origin=meta["origin_xy"]
        wcs=WCS(header).celestial
        jmap,good=dog(data,1.25,3.5)
        for r in records:
            pos=SkyCoord([r["ra1"],r["ra2"]],[r["dec1"],r["dec2"]],unit="deg")
            for name,world in (("j",pos),("shift",pos.directional_offset_by(0*u.deg,3*u.arcsec))):
                x,y=wcs.world_to_pixel(world)
                val=j_check(jmap,good,(x-origin[0],y-origin[1]))
                r.update({f"{name}_{k}":v for k,v in val.items()})
        return tile, {"j":meta},records
    except Exception as exc:
        for r in records:
            r.update(j_state="missing",shift_state="missing")
        return tile,{"j_error":f"{type(exc).__name__}: {exc}"},records


def deduplicate(records):
    positive=[r for r in records if not r["flags"]]
    if not positive:
        return
    coords=SkyCoord([r["ra"] for r in positive],[r["dec"] for r in positive],unit="deg")
    vectors=coords.cartesian.xyz.value.T
    duplicates=cKDTree(vectors).query_pairs(2*np.sin((.3*u.arcsec).to_value(u.rad)/2))
    order={id(r):i for i,r in enumerate(sorted(positive,key=lambda r:(-min(r["vis_score1"],r["vis_score2"]),r["tile"],r["ra"])))}
    for a,b in sorted(duplicates):
        if positive[a]["sign"] != positive[b]["sign"]:
            continue
        loser=max((positive[a],positive[b]),key=lambda r:order[id(r)])
        loser["flags"]="duplicate_midpoint"


def wilson(k,n):
    if not n: return None
    z=1.95996398454
    p=k/n
    ctr=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0,ctr-half),min(1,ctr+half)]


def write_csv(path, records):
    fields=list(dict.fromkeys(k for r in records for k in r))
    with io.StringIO() as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        data=stream.getvalue()
    if path.suffix==".gz":
        path.write_bytes(gzip.compress(data.encode(),mtime=0))
    else:
        path.write_text(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path("results"))
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--tiles", type=int, nargs="+", default=TILES)
    a=parser.parse_args()
    tiles=tuple(dict.fromkeys(a.tiles))
    a.cache.mkdir(parents=True,exist_ok=True)
    a.output.mkdir(parents=True,exist_ok=True)
    indexed={}
    records=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        jobs=[pool.submit(run_vis,t,a.cache) for t in tiles]
        for job in jobs:
            info,rows=job.result()
            indexed[info["tile"]]=info
            records.extend(rows)
            print("VIS",info["tile"],info.get("counts",info.get("vis_error")),flush=True)
        deduplicate(records)
        sign_rows=[r for r in records if not r["flags"] and r["sign"]==1]
        jobs=[pool.submit(run_j,t,a.cache,[r for r in sign_rows if r["tile"]==t]) for t in tiles]
        tested=[]
        for job in jobs:
            t,info,rows=job.result()
            indexed[t].update(info)
            tested.extend(rows)
            print("J",t,sum(r.get("j_state")=="pass" for r in rows),len(rows),info.get("j_error"),flush=True)
    ranked=sorted(tested,key=lambda r:(r.get("j_state")!="pass",
                  -min(r.get("j_score1",0),r.get("j_score2",0)),
                  -min(r["vis_score1"],r["vis_score2"]),r["ra"],r["dec"]))
    for i,r in enumerate(ranked,1):
        r["rank"]=i
        r["id"]=f"EDN-{i:03d}"
    available={"pass","no_repeat","no_local_peak"}
    real=[r for r in tested if r.get("j_state") in available]
    control=[r for r in tested if r.get("shift_state") in available]
    same=[r for r in real if r.get("shift_state") in available]
    j_yes=sum(r["j_state"]=="pass" for r in real)
    sh_yes=sum(r["shift_state"]=="pass" for r in control)
    result={"tiles":list(indexed.values()),"vis_kept_positive":len(sign_rows),
            "vis_kept_negative":sum(not r["flags"] and r["sign"]==-1 for r in records),
            "j_tested":len(real),"j_repeat":j_yes,"j_wilson95":wilson(j_yes,len(real)),
            "shift_tested":len(control),"shift_repeat":sh_yes,
            "paired_n":len(same),"paired_only_real":sum(r["j_state"]=="pass" and r["shift_state"]!="pass" for r in same),
            "paired_only_shift":sum(r["j_state"]!="pass" and r["shift_state"]=="pass" for r in same),
            "active_vis_pixels":sum(x.get("active_vis_pixels",0) for x in indexed.values()),
            "searched_nominal_square_degree":sum(x.get("active_vis_pixels",0) for x in indexed.values())*(.1/3600)**2}
    write_csv(a.output/"signed_vis_pairs.csv.gz",records)
    write_csv(a.output/"candidates.csv",ranked)
    (a.output/"search_summary.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    main()
