"""Show the brightest-component reversal in the original calibrated imaging."""
from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path

from astropy.time import Time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

from holdout_colours import PIXEL
from measure_holdout_colours import components, psf_smoothed

TITLES = {"VIS":"Euclid VIS", "J":"Euclid J", "H":"Euclid H", "i2":"Subaru HSC i2"}
COLOURS = {"VIS":"#245d78","J":"#986420","H":"#a04b3f"}
LIMIT = 1.55


def central_view(data):
    center = data.shape[0]//2
    half = int(LIMIT/PIXEL)
    return data[center-half:center+half+1,center-half:center+half+1]


def stretch(data):
    low, high = np.nanpercentile(data, [7,99.7])
    return np.arcsinh(9*np.clip((data-low)/(high-low),0,1))/np.arcsinh(9)


def rgb(cube, bands, psfs):
    planes = []
    for band in ("H","J","VIS"):
        image = cube[band]
        value = psf_smoothed(image, psfs[band]["central_stamp_fwhm_arcsec"], .65)
        # AB zeropoints bring the units to a common scale before the display stretch.
        value = (value-np.median(value))*10**(.4*(25.-bands[band]["magzero"]))
        planes.append(central_view(value))
    channels = np.maximum(np.stack(planes,axis=-1),0)
    luminance = channels.mean(axis=-1)
    bright = np.quantile(luminance, .995)
    scale = np.divide(np.arcsinh(8*luminance/bright)/np.arcsinh(8),luminance,
                      out=np.zeros_like(luminance),where=luminance>0)
    colour = channels*scale[...,None]
    return colour/np.maximum(colour.max(axis=-1,keepdims=True),1.)


def draw_band(ax, image, title, points):
    ax.imshow(image, extent=(-LIMIT,LIMIT,-LIMIT,LIMIT), origin="lower", interpolation="nearest",
              cmap="gray", vmin=0, vmax=1)
    for (x,y), label in zip(points, ("A","B")):
        ax.add_patch(Circle((x,y),.28,fill=False,lw=.9,edgecolor="#bcebef",alpha=.95))
        ax.text(x+.41,y,label,fontsize=9,color="white",va="center",weight="bold")
    ax.set_axis_off()
    ax.set_title(title,loc="left",size=11,weight="bold",pad=7)


def draw_visits(ax, detail):
    dates = [datetime.fromisoformat(Time(r["VIS"]["mjd"],format="mjd").to_datetime().isoformat())
             for r in detail["visits"].values()]
    for band in ("VIS","J","H"):
        vals = [r[band]["apertures"] for r in detail["visits"].values()]
        y = np.array([r["0.28"]["b_minus_a_aperture_mag"] for r in vals])
        low = np.array([min(v["b_minus_a_aperture_mag"] for v in r.values()) for r in vals])
        high = np.array([max(v["b_minus_a_aperture_mag"] for v in r.values()) for r in vals])
        ax.errorbar(dates,y,yerr=[y-low,high-y],lw=1.3,marker="o",ms=4.,capsize=3,
                    color=COLOURS[band],label=band)
    ax.axhline(0,color=".5",lw=.75)
    ax.set_title("Separate Euclid visits",loc="left",size=11,weight="bold",pad=7)
    ax.set_ylabel("B minus A aperture magnitude")
    ax.set_xticks(dates,[d.strftime("%b %Y") for d in dates],fontsize=8)
    ax.legend(ncol=3,loc="center",frameon=False,fontsize=8)
    ax.set_ylim(-2.05,1.1)
    ax.tick_params(axis="y",labelsize=8)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y",alpha=.12)


def main(cache, output):
    selected = json.loads((cache/"selection.json").read_text())
    target = selected["candidates"][0]
    visits = json.loads((cache/"visit_checks.json").read_text())
    phot = json.loads((cache/"aperture_checks.json").read_text())
    points = components(target)
    name = target["candidate"]
    fig, axes = plt.subplots(2,3,figsize=(10.8,7.4))
    fig.subplots_adjust(left=.075,right=.97,top=.83,bottom=.14,hspace=.20,wspace=.27)
    fig.text(.075,.950,f"{name} · A compact pair that reverses brightness",weight="bold",size=18)
    fig.text(.075,.912,f"Euclid Deep Field North   ·   0.800″ separation   ·   "
             f'{target["ra"]:.6f}°, +{target["dec"]:.6f}° (ICRS)',size=10)
    with np.load(cache/f"{name}.npz") as image:
        for ax, band in zip(axes.flat,("VIS","J","H","i2")):
            draw_band(ax,stretch(central_view(image[band])),TITLES[band],points)
        view = rgb(image,selected["mosaics"][name],phot["lead_psf_metadata"])
        draw_band(axes[1,1],view,"Euclid false-colour composite",points)
    draw_visits(axes[1,2],visits)
    ax = axes[0,0]
    ax.plot([-.95,.05],[-1.19,-1.19],color="white",lw=1.)
    ax.text(-.45,-1.09,"1″",ha="center",size=8,color="white")
    fig.text(.075,.079,"North up, east left. Individual bands use separate display stretches. Composite maps H/J/VIS to red/green/blue.",
             size=8.7)
    fig.text(.075,.053,"Visit error bars span three aperture radii. Negative values indicate that B is brighter within the apertures.",
             size=8.7)
    fig.text(.075,.028,"Biswajit Jana  ·  ESA / Euclid / Euclid Consortium / NASA IRSA and Subaru WISHES imaging",
             size=8.5,color="#3c4a50")
    fig.savefig(output,dpi=152)
    plt.close(fig)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    main(args.cache,args.output)
