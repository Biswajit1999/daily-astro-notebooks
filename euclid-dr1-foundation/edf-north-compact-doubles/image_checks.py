"""Describe image profiles and archive selection by angular separation."""
import csv
import json
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.signal import find_peaks

from search_doubles import wilson

R=Path("results")
COLOURS={"VIS":"#186b86","J":"#b75b29","HSC_I2":"#262027"}


def profile(data,x,y,z):
    center=(x.mean(),y.mean())
    delta=np.array([x[1]-x[0],y[1]-y[0]])
    direction=delta/np.linalg.norm(delta)
    normal=np.array([-direction[1],direction[0]])
    coords=np.asarray(center)[:,None,None]+direction[:,None,None]*z[None,:,None]/.1+normal[:,None,None]*np.array([-1,0,1])[None,None,:]
    a=map_coordinates(data,[coords[1],coords[0]],order=1,prefilter=False,cval=np.nan).mean(axis=1)
    return a-np.nanmedian(a[np.abs(z)>1.6])


def peaks(p,z,sep):
    indices,_=find_peaks(p)
    picked=[]
    for center in (-sep/2,sep/2):
        available=[i for i in indices if abs(z[i]-center)<=.18]
        if not available: return {"state":"no_two_maxima"}
        picked.append(max(available,key=lambda i:p[i]))
    a,b=picked
    if a>=b or min(p[a],p[b])<=0:
        return {"state":"no_two_maxima"}
    dip=float(1-p[a:b+1].min()/min(p[a],p[b]))
    return {"state":"two_maxima" if dip>=.10 else "shallow_saddle","dip":dip,
            "peak_offsets_arcsec":[float(z[a]),float(z[b])]}


def plot_profiles(audit):
    fig, axes=plt.subplots(2,3,figsize=(10,5.2),sharex=True,layout="constrained")
    z=np.arange(-2.0,2.001,.025)
    results={}
    for ax,(name,row) in zip(axes.flat,audit.items(),strict=True):
        out=R/"audit"/name
        target=row["candidate"]
        sep=float(target["sep_arcsec"])
        with fits.open(out/"registered.fits.gz",memmap=False) as dat:
            w=WCS(dat["VIS"].header).celestial
            x,y=w.world_to_pixel_values([target["ra1"],target["ra2"]],[target["dec1"],target["dec2"]])
            vals={}
            for b in COLOURS:
                if b in dat:
                    vals[b]=profile(dat[b].data,x,y,z)
            if "VIS" in dat:
                for blur in (.55,.70,.90):
                    sigma=np.sqrt(blur**2-.18**2)/(2.35482*.1)
                    vals[f"VIS_blur_{blur:.2f}"]=profile(gaussian_filter(dat["VIS"].data,sigma),x,y,z)
        results[name]={k:peaks(v,z,sep) for k,v in vals.items()}
        for band,line in vals.items():
            if band in COLOURS and np.isfinite(line).all():
                ax.plot(z,line/max(line.max(),1e-12),label=band.replace("HSC_I2","Subaru HSC i2"),
                        lw=1.3,color=COLOURS[band])
            elif band=="VIS_blur_0.70":
                ax.plot(z,line/max(line.max(),1e-12),":",lw=1.35,label='VIS to 0.70″',color="#7d5ba6")
        ax.axvline(-sep/2,color="0.55",lw=.65)
        ax.axvline(sep/2,color="0.55",lw=.65)
        ax.set(title=f"{name}  ·  {sep:.2f}″",xlim=(-1.65,1.65),ylim=(-.18,1.1))
        ax.grid(alpha=.13)
    for ax in axes[-1]: ax.set_xlabel("Along pair axis (arcsec)")
    for ax in axes[:,0]: ax.set_ylabel("Normalised profile")
    axes[0,-1].legend(fontsize=7,loc="lower right")
    fig.savefig(R/"profiles.png",dpi=180)
    plt.close(fig)
    return results


def plot_sample(rows,audit):
    bins=(.38,.50,.62,.74,.86,.950001)
    report=[]
    for a,b in zip(bins[:-1],bins[1:],strict=True):
        subset=[r for r in rows if a<=float(r["sep_arcsec"])<b]
        test=[r for r in subset if r["j_state"] in {"pass","no_repeat","no_local_peak"}]
        repeat=sum(r["j_state"]=="pass" for r in test)
        report.append({"lo":a,"hi":b,"tested":len(test),"j_repeat":repeat,"wilson95":wilson(repeat,len(test))})
    fig, ax=plt.subplots(figsize=(6.2,3.2),layout="constrained")
    for bin in report:
        x=(bin["lo"]+bin["hi"])/2
        n=bin["tested"]
        frac=bin["j_repeat"]/n
        lo,hi=bin["wilson95"]
        ax.errorbar(x,frac,xerr=[x-bin["lo"]],yerr=[[frac-lo],[hi-frac]],
                    color="#186b86",fmt="o",capsize=3)
        ax.text(x,hi+.012,f'{bin["j_repeat"]}/{n}',ha="center",fontsize=8)
    ax.set(xlabel="VIS peak separation (arcsec)",ylabel="NISP J repeat fraction",
           ylim=(0,max(i["wilson95"][1] for i in report)+.05))
    ax.grid(alpha=.2)
    fig.savefig(R/"separation.png",dpi=170)
    plt.close(fig)
    return report


if __name__=="__main__":
    audit=json.loads((R/"audit.json").read_text())
    with (R/"candidates.csv").open() as f:
        rows=list(csv.DictReader(f))
    result={"profiles":plot_profiles(audit),"by_separation":plot_sample(rows,audit),
            "method":"Exploratory common-axis profile, ±0.1 arcsec perpendicular average, background from |x| > 1.6 arcsec. Peak search ±0.18 arcsec and minimum 10% saddle. HSC PSF not empirically measured; Gaussian smoothing of VIS only is illustrative."}
    (R/"image_checks.json").write_text(json.dumps(result,indent=2)+"\n")
