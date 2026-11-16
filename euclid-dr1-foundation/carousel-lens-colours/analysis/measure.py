"""Measure image-plane contrasts of spectroscopically identified Carousel arcs."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from scipy.ndimage import gaussian_filter
from scipy.stats import median_abs_deviation

BANDS = ("VIS", "Y", "J", "H")
COMPARISONS = (("1a","1b"), ("1a","2a"), ("1b","2a"), ("3a","3b"), ("3a","3c"),
               ("3b","3c"), ("4a","4b"), ("4a","4c"), ("4a","4d"),
               ("4b","4c"), ("4b","4d"), ("4c","4d"))
# Sizes in arcsec. The matched run is a sensitivity check with nominal PSFs.
NOMINAL_FWHM = {"VIS": 0.18, "Y": 0.49, "J": 0.51, "H": 0.56}
SETUPS = {
    "nominal": (.8, 1.25, 2.25, False),
    "small": (.65, 1.25, 2.25, False),
    "large": (1., 1.25, 2.25, False),
    "outer_sky": (.8, 1.5, 2.5, False),
    "matched": (.8, 1.25, 2.25, True),
}


def aperture(image, valid, x, y, others, radii, scale):
    radius, inner, outer = radii
    half = int(np.ceil(outer / scale)) + 1
    ix, iy = round(x), round(y)
    if not (half <= ix < image.shape[1]-half and half <= iy < image.shape[0]-half):
        return None
    sl = np.s_[iy-half:iy+half+1, ix-half:ix+half+1]
    yy, xx = np.mgrid[iy-half:iy+half+1, ix-half:ix+half+1]
    distance = np.hypot(xx-x, yy-y)*scale
    source = distance <= radius
    ok = valid[sl]
    if np.count_nonzero(source & ok) < .95*np.count_nonzero(source):
        return None
    sky = (distance >= inner) & (distance <= outer) & ok
    for ox, oy in others:
        if np.hypot(ox-x,oy-y)*scale <= outer+0.8:
            sky &= np.hypot(xx-ox, yy-oy)*scale >= .8
    if np.count_nonzero(sky) < .5*np.count_nonzero((distance >= inner) & (distance <= outer)):
        return None
    design = np.stack([np.ones_like(xx), (xx-x)*scale, (yy-y)*scale],axis=-1)
    planes = design[sky]
    values = image[sl][sky]
    keep = np.ones(len(values), dtype=bool)
    for _ in range(3):
        coef = np.linalg.lstsq(planes[keep], values[keep], rcond=None)[0]
        resid = values-planes@coef
        scatter = median_abs_deviation(resid[keep], scale="normal")
        if not np.isfinite(scatter) or scatter <= 0:
            return None
        keep = np.abs(resid-np.median(resid[keep])) < 3*scatter
        if keep.sum() < len(values)/2:
            return None
    coef = np.linalg.lstsq(planes[keep], values[keep], rcond=None)[0]
    src = source & ok
    return float(np.sum(image[sl][src]-design[src]@coef)*source.sum()/src.sum())


def measure(images, positions):
    rows = []
    for config, (radius, inner, outer, smooth) in SETUPS.items():
        for band, (image, valid, wcs) in images.items():
            scale = float(proj_plane_pixel_scales(wcs)[0]*3600)
            xy = np.column_stack(wcs.world_to_pixel(positions))
            if smooth:
                sigma = np.sqrt(.85**2-NOMINAL_FWHM[band]**2) / (2.35482*scale)
                weight = gaussian_filter(valid.astype(float), sigma)
                image = gaussian_filter(np.where(valid,image,0.), sigma) / np.maximum(weight,1e-12)
                valid = valid & (weight >= .99)
            for i,(x,y) in enumerate(xy):
                label = positions.info.meta["labels"][i]
                if label not in {v for pair in COMPARISONS for v in pair}:
                    continue
                radii = (radius, inner, outer)
                flux = aperture(image, valid, x, y, np.delete(xy,i,axis=0), radii, scale)
                blank = []
                for ring,angles in [(4,8),(7,12),(10,16)]:
                    for phi in np.arange(angles)*2*np.pi/angles:
                        bx,by = x + ring*np.cos(phi)/scale, y + ring*np.sin(phi)/scale
                        if np.min(np.hypot(xy[:,0]-bx,xy[:,1]-by))*scale < radius+.8:
                            continue
                        value = aperture(image,valid,bx,by,xy,radii,scale)
                        if value is not None:
                            blank.append(value)
                noise = float(median_abs_deviation(blank,scale="normal")) if len(blank)>=12 else None
                snr = flux/noise if flux is not None and noise is not None and noise>0 else None
                rows.append(dict(setup=config, arc=label, band=band, flux=flux,
                                 local_scatter=noise, n_controls=len(blank), snr=snr))
    return rows


def differences(rows):
    lookup = {(r["setup"],r["arc"],r["band"]): r for r in rows}
    output = []
    for setup in SETUPS:
        for a,b in COMPARISONS:
            for band in BANDS[:-1]:
                terms = [lookup[setup,arc,f] for arc,f in [(a,band),(a,"H"),(b,band),(b,"H")]]
                if any(r["snr"] is None or r["snr"]<3 for r in terms):
                    delta = sigma = None
                else:
                    f1,h1,f2,h2 = [r["flux"] for r in terms]
                    delta = float(-2.5*np.log10((f1/h1)/(f2/h2)))
                    sigma = float((2.5/np.log(10))*np.sqrt(sum(r["snr"]**-2 for r in terms)))
                output.append(dict(setup=setup, arc_a=a, arc_b=b, colour=f"{band}-H",
                                   delta_mag=delta, local_error_mag=sigma))
    return output


def figures(images, positions, contrasts, out):
    fig,axs=plt.subplots(1,2,figsize=(9,4.1),layout="constrained")
    for band,ax in zip(("VIS","H"),axs):
        image,mask,wcs=images[band]
        scale=proj_plane_pixel_scales(wcs)[0]*3600
        cx,cy=wcs.world_to_pixel_values(90.985416667,-35.9683)
        ext=np.array([-.5-cx,image.shape[1]-.5-cx,-.5-cy,image.shape[0]-.5-cy])*scale
        peak=np.nanpercentile(image[mask],99.85)
        ax.imshow(np.arcsinh(image/(peak/12)),origin="lower",extent=ext,cmap="gray",
                  vmin=-.35,vmax=np.arcsinh(12))
        xy=np.column_stack(wcs.world_to_pixel(positions))
        for label,(xp,yp) in zip(positions.info.meta["labels"],xy):
            if label not in {"1a","1b","2a","3a","3b","3c","4a","4b","4c","4d"}:
                continue
            x,y=(xp-cx)*scale,(yp-cy)*scale
            color="#ffce73" if label in {"1a","1b","2a"} else "#7de3de"
            ax.add_patch(plt.Circle((x,y),.8,fill=False,lw=1.1,color=color))
            ax.text(x+.95,y+.7,label,color=color,fontsize=8)
        ax.set(xlim=(-23,23),ylim=(-22,22),title=f"Euclid {band}",xlabel="Mosaic x offset [arcsec]")
    axs[0].set_ylabel("Mosaic y offset [arcsec]")
    fig.savefig(out/"carousel_euclid.png",dpi=155)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4.8),layout="constrained")
    colors={"nominal":"#25456f","small":"#8c6741","large":"#40735a","outer_sky":"#783d76","matched":"#b43d43"}
    shown=[(a,b) for a,b in COMPARISONS if any(c["arc_a"]==a and c["arc_b"]==b and c["colour"]=="Y-H" and c["delta_mag"] is not None for c in contrasts)]
    for j,(setup,color) in enumerate(colors.items()):
        valid=[c for c in contrasts if c["setup"]==setup and c["colour"]=="Y-H" and c["delta_mag"] is not None]
        ax.errorbar([c["delta_mag"] for c in valid],
                    [shown.index((c["arc_a"],c["arc_b"]))+(j-2)*.10 for c in valid],
                    xerr=[c["local_error_mag"] for c in valid],fmt="o",ms=4,color=color,label=setup)
    ax.axvline(0,color=".65",lw=1)
    ax.set(yticks=range(len(shown)),yticklabels=[f"{a} − {b}" for a,b in shown],xlabel="Difference in aperture Y − H colour [mag]")
    ax.invert_yaxis()
    ax.legend(loc="best",fontsize=8)
    fig.savefig(out/"colour_contrasts.png",dpi=155)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--arcs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with args.arcs.open() as file:
        arcs=list(csv.DictReader(file))
    positions=SkyCoord([r["ra_hms"] for r in arcs],[r["dec_dms"] for r in arcs],
                       unit=("hourangle","deg"))
    positions.info.meta={"labels":[r["image"] for r in arcs]}
    images={}
    for band in BANDS:
        data,header=fits.getdata(args.data/f"{band}.fits",header=True)
        flags,flag_header=fits.getdata(args.data/f"{band}_flag.fits",header=True)
        wcs=WCS(header)
        assert data.shape==flags.shape
        np.testing.assert_allclose(wcs.world_to_pixel(positions),WCS(flag_header).world_to_pixel(positions),atol=.01)
        images[band]=(data,np.isfinite(data)&((flags&1)==0),wcs)
    rows=measure(images,positions)
    contrasts=differences(rows)
    for name,items in [("apertures",rows),("colour_differences",contrasts)]:
        with (args.output/f"{name}.csv").open("w",newline="") as file:
            writer=csv.DictWriter(file,fieldnames=items[0].keys(),lineterminator="\n")
            writer.writeheader()
            writer.writerows(items)
    figures(images,positions,contrasts,args.output)
    for item in contrasts:
        if item["arc_a"]=="1a" and item["colour"]=="Y-H":
            print(json.dumps(item))


if __name__=="__main__":
    main()
