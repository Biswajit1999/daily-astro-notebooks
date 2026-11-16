"""Build discovery maps for the fixed S4G sample."""
import argparse
import csv
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.io import fits
import astropy.units as u
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter, label
from scipy.stats import median_abs_deviation


def maps(image, east, north, radius, axis_ratio, pa):
    p=np.radians(pa)
    major=east*np.sin(p)+north*np.cos(p)
    minor=east*np.cos(p)-north*np.sin(p)
    elliptical=np.hypot(major,minor/axis_ratio)
    radial=np.hypot(east,north)
    good=np.isfinite(image)&(image!=0)
    valid=np.where(good,image,np.nan)
    bins=np.minimum((elliptical/2).astype(int),800)
    model=np.zeros(801)
    # Use sorted bin indices once, and compare each bin with its peers in the ellipse.
    flat_bin=bins[good]
    order=np.argsort(flat_bin,kind="stable")
    values=valid[good][order]
    counts=np.bincount(flat_bin,minlength=len(model))
    lim=np.cumsum(np.r_[0,counts])
    for i in np.flatnonzero(counts>=20):
        model[i]=np.median(values[lim[i]:lim[i+1]])
    residual=image-model[bins]
    geometry=(elliptical>=1.15*radius)&(radial>=40)&(radial<=105)
    return residual,good,geometry,elliptical


def smooth_map(residual,good,spacing,sigma,clip):
    valid=good&(np.abs(residual)<clip)
    blurred=gaussian_filter(np.where(valid,residual,0.),sigma/spacing)
    weight=gaussian_filter(valid.astype(float),sigma/spacing)
    return np.where(weight>.65,blurred/np.maximum(weight,1e-9),np.nan)


def load_maps(row, path, sky_path=None):
    im,header=fits.getdata(path,header=True)
    wcs=WCS(header).celestial
    pixel_scale = np.abs(wcs.pixel_scale_matrix.diagonal()) * 3600
    factor=round(.5 / pixel_scale[0])
    if factor not in (1,5) or not np.allclose(
        wcs.pixel_scale_matrix*3600, np.diag([-.5/factor,.5/factor]), atol=.002
    ):
        raise ValueError("Expected a 0.1 or 0.5 arcsec north-up image grid")
    if sky_path is not None:
        sky,sky_header=fits.getdata(sky_path,header=True)
        sky_wcs=WCS(sky_header).celestial
        if im.shape!=sky.shape or not np.allclose(sky_wcs.wcs.crpix,wcs.wcs.crpix) or not np.allclose(
            sky_wcs.wcs.crval,wcs.wcs.crval,atol=1e-8,rtol=0
        ) or not np.array_equal(sky_wcs.pixel_scale_matrix,wcs.pixel_scale_matrix):
            raise ValueError("MER background and science grids differ")
        im=np.where(np.isfinite(im)&(im!=0),im+sky,np.nan)
    middle=(factor-1)/2
    ny,nx=(np.array(im.shape)//factor)*factor
    blocks=im[:ny,:nx].reshape(ny//factor,factor,nx//factor,factor)
    numeric=np.isfinite(blocks)&(blocks!=0)
    image=np.ma.median(np.ma.masked_where(~numeric,blocks),axis=(1,3)).filled(np.nan)
    image[numeric.sum(axis=(1,3))<=factor**2//2]=np.nan
    center=SkyCoord(float(row["ra"]),float(row["dec"]),unit="deg")
    center_x,center_y=wcs.world_to_pixel(center)
    yy,xx=np.indices(image.shape)
    sky=wcs.pixel_to_world(xx*factor+middle,yy*factor+middle)
    offsets=center.spherical_offsets_to(sky)
    east,north=(part.to_value(u.arcsec) for part in offsets)
    radius=float(row["sma1_25p5"])
    ratio=1-float(row["ellip1_25p5"])
    pa=float(row["pa1_25p5"])
    residual,good,geometry,elliptical=maps(image,east,north,radius,ratio,pa)
    return image,residual,good,geometry,elliptical,east,north,wcs,((center_x-middle)/factor,(center_y-middle)/factor)


def fit_target(row,path):
    image,residual,good,geometry,elliptical,east,north,wcs,center=load_maps(row,path)
    spacing=.5
    search=good&geometry
    if np.count_nonzero(search)<80:
        raise ValueError("No usable VIS pixels in the search region")
    scatter=median_abs_deviation(residual[search],scale="normal")
    if not np.isfinite(scatter) or scatter<=0:
        raise ValueError("Search region is unavailable")
    # Clip compact bright sources relative to the local elliptical baseline.
    fine=smooth_map(residual,good,spacing,1.5,6*scatter)
    coarse=smooth_map(residual,good,spacing,3,6*scatter)
    scale_fine=median_abs_deviation(fine[search&np.isfinite(fine)],scale="normal")
    scale_coarse=median_abs_deviation(coarse[search&np.isfinite(coarse)],scale="normal")
    if not min(scale_fine,scale_coarse)>0 or not np.all(np.isfinite([scale_fine,scale_coarse])):
        raise ValueError("Smoothed background scatter is unavailable")
    z_fine,z_coarse=fine/scale_fine,coarse/scale_coarse
    components,n=label(search&(z_fine>2)&(z_coarse>3),structure=np.ones((3,3)))
    candidates=[]
    for i in range(1,n+1):
        yy,xx=np.where(components==i)
        if len(yy)<80:
            continue
        y,x=yy[np.nanargmax(z_coarse[yy,xx])],xx[np.nanargmax(z_coarse[yy,xx])]
        variances=np.linalg.eigvalsh(np.cov(np.vstack([east[yy,xx],north[yy,xx]])))
        elongation=float(np.sqrt(variances[1]/variances[0]))
        sx,sy=x*5+2,y*5+2
        ra,dec=wcs.pixel_to_world_values(sx,sy)
        candidates.append(dict(target=row["object"],ra=float(ra),dec=float(dec),east=float(east[y,x]),
                               north=float(north[y,x]),area_arcsec2=len(yy)*spacing**2,
                               peak=float(z_coarse[y,x]),elongation=elongation,
                               rms_major_arcsec=float(np.sqrt(variances[1]))))
    candidates.sort(key=lambda q:q["peak"],reverse=True)
    for rank,candidate in enumerate(candidates,1):
        candidate["id"]=f"{row['object']}-{rank:02d}"
    coverage=float(np.count_nonzero(search)/np.count_nonzero(geometry))
    return image,z_coarse,center,coverage,candidates,elliptical


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("targets",type=Path)
    p.add_argument("cache",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with args.targets.open() as f: rows=list(csv.DictReader(f))
    fig,axes=plt.subplots(4,4,figsize=(13,12),layout="constrained")
    results=[]
    for i,row in enumerate(rows):
        name=row["object"]
        figpos=(i//2,(i%2)*2)
        panels=axes[figpos[0],figpos[1]:figpos[1]+2]
        try:
            image,resid,center,coverage,candidates,elliptical=fit_target(row,args.cache/f"{name}_vis.fits")
        except (FileNotFoundError,ValueError) as exc:
            results.append(dict(target=name,error=str(exc)))
            for ax in panels:
                ax.set_axis_off()
                ax.set_title(name+" unavailable")
            continue
        print(name,coverage,len(candidates),[(round(c["east"]),round(c["north"]),round(c["peak"],2)) for c in candidates],flush=True)
        results.append(dict(target=name,coverage_within_stamp=coverage,candidates=candidates))
        cx,cy=center
        extent=[(-.5-cx)*.5,(image.shape[1]-.5-cx)*.5,(-.5-cy)*.5,(image.shape[0]-.5-cy)*.5]
        sky=np.nanpercentile(image,[50,98])
        panels[0].imshow(np.arcsinh((image-sky[0])*18/(sky[1]-sky[0])),extent=extent,
                         origin="lower",cmap="gray",vmin=-.2,vmax=3.6)
        panels[1].imshow(resid,extent=extent,origin="lower",cmap="RdBu_r",vmin=-4,vmax=4)
        for k,ax in enumerate(panels):
            xgrid=(np.arange(image.shape[1])-cx)*.5
            ygrid=(np.arange(image.shape[0])-cy)*.5
            ax.contour(xgrid,ygrid,elliptical,levels=[1.15*float(row["sma1_25p5"])],
                       linestyles="--",colors="#c3c75a",linewidths=.75,alpha=.9)
            for c in candidates:
                ax.scatter(-c["east"],c["north"],s=30,facecolor="none",edgecolor="#24d4ba",linewidth=.8)
            ax.set(xlim=(-108,108),ylim=(-108,108),title=f"{name} · "+("VIS" if k==0 else "residual"),
                   xticks=[],yticks=[])
    fig.savefig(args.output/"pilot_fields.png",dpi=105)
    (args.output/"results.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__":
    main()
