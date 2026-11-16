"""Measure VIS-selected positions in restored VIS and independent images."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from scipy.stats import median_abs_deviation

from quicklook import load_maps, smooth_map

BANDS = ("vis", "restored_vis", "legacy_r", "h")
RADIUS = 5
GRID = .5


def load_band(row, band, directory):
    name = row["object"]
    science = directory / f"{name}_{'vis' if band == 'restored_vis' else band}.fits"
    background = directory / f"{name}_vis_sky.fits" if band == "restored_vis" else None
    image, residual, good, region, _, _, _, _, center = load_maps(row, science, background)
    sample = residual[good & region]
    if len(sample) < 80:
        raise ValueError("No usable pixels in search region")
    scatter = median_abs_deviation(sample, scale="normal")
    if not np.isfinite(scatter) or scatter <= 0:
        raise ValueError("Background scatter is unavailable")
    return image, residual, good & (np.abs(residual) < 6 * scatter), center, scatter


def aperture(residual, valid, center, east, north):
    x, y = center[0] - east / GRID, center[1] + north / GRID
    ry = np.arange(round(y) - 11, round(y) + 12)
    rx = np.arange(round(x) - 11, round(x) + 12)
    if ry[0] < 0 or rx[0] < 0 or ry[-1] >= residual.shape[0] or rx[-1] >= residual.shape[1]:
        return None
    interior = ((rx[None, :] - x)**2 + (ry[:, None] - y)**2) * GRID**2 <= RADIUS**2
    keep = valid[np.ix_(ry, rx)] & interior
    if np.count_nonzero(keep) < .65 * np.count_nonzero(interior):
        return None
    return float(residual[np.ix_(ry, rx)][keep].mean())


def measure(row, candidate, data):
    _, residual, valid, center, _ = data
    east, north = candidate["east"], candidate["north"]
    value = aperture(residual, valid, center, east, north)
    if value is None:
        return None
    pa = np.deg2rad(float(row["pa1_25p5"]))
    ratio = 1 - float(row["ellip1_25p5"])
    major, minor = east*np.sin(pa)+north*np.cos(pa), east*np.cos(pa)-north*np.sin(pa)
    phase = np.arctan2(minor/ratio, major)
    rho = np.hypot(major, minor/ratio)
    previous = [(east, north)]
    controls = []
    for angle in phase + np.deg2rad(np.arange(5, 360, 5)):
        major, minor = rho*np.cos(angle), ratio*rho*np.sin(angle)
        e, n = major*np.sin(pa)+minor*np.cos(pa), major*np.cos(pa)-minor*np.sin(pa)
        if not 40 <= np.hypot(e, n) <= 105 or any(np.hypot(e-a, n-b) < 2*RADIUS for a,b in previous):
            continue
        trial = aperture(residual, valid, center, e, n)
        if trial is not None:
            controls.append(trial)
            previous.append((e,n))
    return {"mean": value, "n_control": len(controls),
            "control_median": float(np.median(controls)) if controls else None,
            "rank_fraction": (sum(v < value for v in controls) / len(controls)) if controls else None}


def panel(ax, data, candidate, residual_panel):
    image, residual, valid, center, scatter = data
    e,n=candidate["east"],candidate["north"]
    yy,xx=np.indices(image.shape)
    x= (xx-center[0])*GRID
    y= (yy-center[1])*GRID
    extent=[x[0,0]-GRID/2,x[0,-1]+GRID/2,y[0,0]-GRID/2,y[-1,0]+GRID/2]
    if residual_panel:
        shown = smooth_map(residual, valid, GRID, 1.5, np.inf)/scatter
        ax.imshow(shown, extent=extent, origin="lower", cmap="RdBu_r", vmin=-1.5, vmax=1.5)
    else:
        window=(np.abs(x+e)<18)&(np.abs(y-n)<18)&np.isfinite(image)
        if np.count_nonzero(window)<10:
            return
        level, bright=np.quantile(image[window],[.40,.99])
        spread=max(bright-level,np.finfo(float).eps)
        shown = np.arcsinh((image-level)*8/spread)
        ax.imshow(shown,extent=extent,origin="lower",cmap="gray",vmin=-.5,vmax=3.5)
    ax.add_patch(Circle((-e,n),RADIUS,edgecolor="#3df0bc",facecolor="none",linewidth=.85))
    ax.set(xlim=(-e-18,-e+18),ylim=(n-18,n+18))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets",type=Path)
    parser.add_argument("cache",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--elongated",action="store_true",help="Plot the elongated VIS candidates")
    args=parser.parse_args()
    with args.targets.open() as stream:
        rows={row["object"]:row for row in csv.DictReader(stream)}
    results=json.loads((args.output/"results.json").read_text())
    measured=[]
    diagnostics={}
    selected = {
        name: [q for q in result.get("candidates", [])
               if q["elongation"] >= 2 and q["rms_major_arcsec"] >= 4]
        for result in results
        for name in (result["target"],)
    }
    if not args.elongated:
        selected = {result["target"]:result.get("candidates", [])[:1] for result in results}
    n_panels = max(1, sum(map(len, selected.values())))
    fig, grid=plt.subplots(n_panels,4,figsize=(8.5,1.85*n_panels),layout="constrained",squeeze=False)
    active=0
    for result in results:
        name=result["target"]
        if not result.get("candidates"):
            continue
        row=rows[name]
        data={}
        diagnostics[name]={}
        for band in BANDS:
            try:
                data[band]=load_band(row,band,args.cache)
            except (OSError,ValueError) as exc:
                diagnostics[name][band]=str(exc).replace(str(args.cache)+"/","")
        for candidate in result["candidates"]:
            checks={band:measure(row,candidate,values) for band,values in data.items()}
            measured.append({**candidate,"checks":checks})
        for candidate in selected[name]:
            for ax,band,title in zip(grid[active],("vis","restored_vis","legacy_r","h"),
                                     ("Euclid VIS","Restored VIS residual","Legacy DR10 r","Euclid NISP H")):
                ax.set(xticks=[],yticks=[])
                if active==0:
                    ax.set_title(title,fontsize=10)
                if band in data:
                    panel(ax,data[band],candidate,band=="restored_vis")
                else:
                    ax.text(.5,.5,"Unavailable",transform=ax.transAxes,ha="center",va="center")
                if band=="vis":
                    ax.set_ylabel(candidate["id"])
            active+=1
    for ax in grid[active:].flat:
        ax.axis("off")
    plot = "elongated_checks.png" if args.elongated else "cross_checks.png"
    fig.savefig(args.output/plot,dpi=95)
    (args.output/"cross_checks.json").write_text(
        json.dumps({"unavailable":diagnostics,"candidates":measured},indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
