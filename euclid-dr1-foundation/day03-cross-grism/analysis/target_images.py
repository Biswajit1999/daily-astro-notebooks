"""Fetch and show observed VIS thumbnails for the two Day 3 spectrum examples."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import sys

from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/"nearby-galaxy-outskirts"/"analysis"))
from fetch import extract, list_keys

LABELS = {
    "2693214850660403334": "Red-bin removal example",
    "2695057816657579082": "DESI-redshift example",
}


def observed_target(row, cache):
    keys = [key for key in list_keys(row["tile"],"VIS")
            if "BGSUB-MOSAIC-VIS_" in key and key.endswith(".fits")]
    if len(keys) != 1:
        raise ValueError(f"Expected one VIS mosaic for tile {row['tile']}")
    ra, dec = float(row["ra"]), float(row["dec"])
    path = cache/f"{row['object']}_vis.fits"
    provenance = extract(keys[0],ra,dec,path,half_size=65,stripe_rows=130)
    pixels,header = fits.getdata(path,header=True)
    wcs = WCS(header).celestial
    x,y = map(float,wcs.world_to_pixel_values(ra,dec))
    scale = abs(wcs.pixel_scale_matrix[0,0])*3600
    if not (np.isfinite(x+y) and 0<=x<pixels.shape[1] and 0<=y<pixels.shape[0]):
        raise ValueError(f"Target {row['object']} outside its image")
    yy,xx = np.indices(pixels.shape)
    valid = np.isfinite(pixels)&(pixels!=0)
    local = valid & (np.hypot(xx-x,yy-y) <= 20)
    if np.count_nonzero(local) < 800:
        raise ValueError(f"Target {row['object']} lacks central coverage")
    return pixels,valid,x,y,scale,dict(row,**provenance)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache",type=Path)
    p.add_argument("output",type=Path)
    args = p.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True)
    args.output.mkdir(parents=True,exist_ok=True)
    with (HERE/"target_image_positions.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    with ThreadPoolExecutor(2) as pool:
        data = list(pool.map(lambda row: observed_target(row,args.cache),rows))
    fig,axes = plt.subplots(1,2,figsize=(7.5,4.0),layout="constrained")
    records = []
    for ax,(pixels,valid,x,y,scale,record) in zip(axes,data):
        lo,hi = np.percentile(pixels[valid],[25,99.8])
        ny,nx = pixels.shape
        extent = [(-.5-x)*scale,(nx-.5-x)*scale,(-.5-y)*scale,(ny-.5-y)*scale]
        ax.imshow(np.where(valid,pixels,np.nan),origin="lower",extent=extent,cmap="gray",
                  norm=ImageNormalize(vmin=lo,vmax=hi,stretch=AsinhStretch(.13)))
        ax.add_patch(Circle((0,0),.65,fill=False,ec="#64e8c4",lw=1.5))
        ax.plot([-5.15,-3.15],[-5.15,-5.15],color="white",lw=2)
        ax.text(-4.15,-4.9,"2″",color="white",ha="center",va="bottom",fontsize=10)
        ax.text(.965,.960,"N ↑\nE ←",ha="right",va="top",color="white",transform=ax.transAxes,fontsize=10)
        ident = record["object"]
        ax.set(xlim=(-6,6),ylim=(-6,6),xticks=[],yticks=[],title=f"{LABELS[ident]}\nMER {ident}")
        records.append(record)
    fig.savefig(args.output/"day3_vis_targets.png",dpi=175,facecolor="white")
    (args.output/"target_image_products.json").write_text(json.dumps(records,indent=2)+"\n")


if __name__=="__main__":
    main()
