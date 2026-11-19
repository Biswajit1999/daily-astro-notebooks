"""Plot native ASKAP RACS-low contours on registered optical FITS images."""
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import mad_std, sigma_clip
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
import numpy as np

LENS = SkyCoord(52.737216, -52.470283, unit="deg", frame="icrs")
ARC = SkyCoord(52.735917, -52.471431, unit="deg", frame="icrs")
TILES = ("0304-50A", "0310-56A")
SIGMAS = np.array([5, 10, 20, 40, 80, 160])


def image(path):
    data, h = fits.getdata(path, header=True, memmap=False)
    data = np.squeeze(data)
    if data.ndim != 2 or not np.isfinite(data).any():
        raise ValueError(f"Expected a usable 2D image in {path}")
    return data.astype(float), WCS(h).celestial, h


def radio_stats(path):
    data, w, h = image(path)
    if u.Unit(h["BUNIT"]) != u.Jy / u.beam or h["CRVAL4"] != 1:
        raise ValueError(f"Expected Stokes I in Jy/beam: {path}")
    if not np.isclose(h["CRVAL3"], 887.491e6, atol=1, rtol=0):
        raise ValueError(f"Unexpected frequency: {path}")
    beam = 3600 * np.array([h["BMAJ"], h["BMIN"]])
    if not np.allclose(beam, 25., atol=.01):
        raise ValueError(f"Expected the common-resolution 25 arcsec beam: {path}")
    y, x = np.indices(data.shape)
    radius = w.pixel_to_world(x, y).separation(LENS).arcsec
    annulus = data[(radius >= 75) & (radius <= 280) & np.isfinite(data)]
    sky = sigma_clip(annulus, sigma=3, maxiters=5, stdfunc=mad_std).compressed()
    if sky.size < 1000:
        raise ValueError(f"Too little valid sky to estimate local noise: {path}")
    background = np.median(sky)
    noise = mad_std(sky)
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError(f"Invalid noise estimate: {path}")
    py, px = np.unravel_index(np.nanargmax(np.where(radius <= 30, data, np.nan)), data.shape)
    peak = w.pixel_to_world(px, py).icrs
    measures = {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "frequency_MHz": h["CRVAL3"] / 1e6,
        "beam_fwhm_arcsec": beam.tolist(),
        "pixel_scale_arcsec": (3600 * proj_plane_pixel_scales(w)).tolist(),
        "local_background_mJy_per_beam": float(1000 * background),
        "local_sigma_mJy_per_beam": float(1000 * noise),
        "annulus_arcsec": [75, 280],
        "annulus_pixels_after_clipping": int(sky.size),
        "peak_pixel_RA_Dec_deg": [peak.ra.deg, peak.dec.deg],
        "peak_above_background_mJy_per_beam": float(1000 * (data[py, px]-background)),
        "peak_pixel_offset_from_lens_arcsec": peak.separation(LENS).arcsec,
        "contour_mJy_per_beam_above_background": (1000 * noise * SIGMAS).tolist(),
    }
    return (data-background)/noise, w, measures


def stretch(data, strength, percentile):
    sky, white = np.nanpercentile(data, [35, percentile])
    scaled = np.clip((data-sky)/(white-sky), 0, 1)
    return np.arcsinh(strength*scaled)/np.arcsinh(strength)


def angular_view(ax, w, coordinate, width, scale_width):
    x, y = map(float, w.world_to_pixel(coordinate))
    sx, sy = proj_plane_pixel_scales(w) * 3600
    halfx, halfy = width/(2*sx), width/(2*sy)
    ax.set_xlim(x-halfx, x+halfx)
    ax.set_ylim(y-halfy, y+halfy)
    for coord in ax.coords:
        coord.set_ticks_visible(False)
        coord.set_ticklabel_visible(False)
        coord.set_axislabel("")
    left, base = x-.83*halfx, y-.83*halfy
    ax.plot([left,left+scale_width/sx],[base,base],c="white",lw=2)
    label = f"{scale_width//60}′" if scale_width >= 60 else f"{scale_width}″"
    ax.text(left+scale_width/(2*sx),base+.045*halfy,label,c="white",ha="center",va="bottom",fontsize=9)
    return x,y,sx,sy


def points(ax, w):
    for position, marker in [(LENS,"+"), (ARC,"x")]:
        x,y = w.world_to_pixel(position)
        ax.plot(x,y,marker=marker,ms=8,mew=1.35,c="#d7baff",zorder=6)


def figure(legacy, legacy_lens, optical, radio, report, out):
    l, lw, _ = legacy
    zoom, zw, _ = legacy_lens
    v, vw, _ = optical
    signal, rw, _ = radio
    field = lw.pixel_to_world((l.shape[1]-1)/2, (l.shape[0]-1)/2)
    tab = report["tiles"][0]
    peak = SkyCoord(*tab["peak_pixel_RA_Dec_deg"], unit="deg", frame="icrs")
    fig = plt.figure(figsize=(12.4, 6.1), facecolor="white")
    grid = fig.add_gridspec(1, 3, left=.047, right=.965, top=.745, bottom=.236, wspace=.12)
    axs = [fig.add_subplot(grid[0,i], projection=w) for i,w in enumerate((lw,zw,vw))]
    fig.text(.047,.935,"Radio emission along the Abell 3128 sightline",fontsize=22,weight="semibold")
    fig.text(.047,.875,"ASKAP RACS-low at 887.5 MHz  |  Legacy Surveys DR10 and Euclid DR1-Foundation",
             fontsize=11,color=".30")
    l_show = stretch(l,90,99.55)
    v_show = stretch(v,28,99.82)
    axs[0].imshow(l_show,origin="lower",cmap="gray",interpolation="nearest",vmin=0,vmax=1)
    axs[1].imshow(stretch(zoom,35,99.7),origin="lower",cmap="gray",interpolation="nearest",vmin=0,vmax=1)
    axs[2].imshow(v_show,origin="lower",cmap="gray",interpolation="nearest",vmin=0,vmax=1)
    for ax in axs[:2]:
        ax.contour(signal,levels=SIGMAS,colors="#ffc25b",linewidths=.73,alpha=.93,
                   transform=ax.get_transform(rw),zorder=3)
        ax.contour(signal,levels=[-5],colors="#bdc7cf",linewidths=.65,linestyles="dashed",
                   transform=ax.get_transform(rw),zorder=3)
    _,_,sx,sy = angular_view(axs[0],lw,field,1360,180)
    cx,cy = lw.world_to_pixel(LENS)
    axs[0].add_patch(Rectangle((cx-90/sx,cy-90/sy),180/sx,180/sy,fill=False,
                              lw=.85,ls=":",ec="white",zorder=4))
    axs[0].text(cx+97/sx,cy+80/sy,"Lens field",va="center",c="white",fontsize=8)
    axs[0].text(.91,.91,"N ↑\nE ←",color="white",fontsize=8,ha="center",transform=axs[0].transAxes)
    cx,cy,sx,sy = angular_view(axs[1],zw,LENS,180,30)
    axs[1].add_patch(Rectangle((cx-14.55/sx,cy-14.55/sy),29.1/sx,29.1/sy,fill=False,
                              lw=.8,ls=":",ec="white",zorder=4))
    axs[1].add_patch(Circle((cx+72/sx,cy-70/sy),12.5/sx,fill=False,lw=1.1,ec="white"))
    axs[1].text(cx+72/sx,cy-52/sy,"Beam",ha="center",color="white",fontsize=8)
    _,_,sx,_ = angular_view(axs[2],vw,LENS,29.1,5)
    px,py = vw.world_to_pixel(peak)
    axs[2].add_patch(Circle((px,py),12.5/sx,fill=False,lw=1,ec="#ffc25b",ls="--"))
    axs[2].plot(px,py,marker="o",mfc="none",mec="#ffc25b",ms=7.5,mew=1)
    points(axs[2],vw)
    labels = ["(a) Cluster sightline · Legacy r", "(b) Lens field · Legacy r", "(c) Optical arc · Euclid VIS"]
    for ax,label in zip(axs,labels,strict=True):
        ax.set_title(label,loc="left",fontsize=11,pad=8)
    fig.legend(handles=[
        Line2D([],[],c="#b16c08",lw=1,label="Positive radio contours"),
        Line2D([],[],c=".45",lw=.85,ls="--",label="−5σ control"),
        Line2D([],[],c="#9254b3",marker="+",linestyle="none",label="Lens galaxy"),
        Line2D([],[],c="#9254b3",marker="x",linestyle="none",label="Optical arc"),
        Line2D([],[],c="#b16c08",ls="--",lw=1,label="25″ FWHM centred on radio peak in (c)"),
    ],loc="upper left",bbox_to_anchor=(.047,.22),ncols=5,fontsize=8.3,frameon=False,
        borderaxespad=0,columnspacing=1.7)
    vals = ", ".join(f"{x:.2f}" for x in tab["contour_mJy_per_beam_above_background"])
    noise = tab["local_sigma_mJy_per_beam"]
    fig.text(.047,.116,f"Contours above the local background at {vals} mJy/beam (5–160σ).  Local σ = {noise:.3f} mJy/beam.",
             fontsize=8.8)
    fig.text(.047,.084,"In (c), the open circle marks the brightest radio pixel. The dashed circle shows the beam footprint at half maximum.",fontsize=8.6)
    fig.text(.047,.047,"Biswajit Jana  |  ASKAP/CSIRO CASDA via CADC · Legacy Surveys DR10 · ESA/Euclid/Euclid Consortium/NASA via IRSA",
             fontsize=8.0,color=".3")
    fig.savefig(out/"Abell3128_Radio_Optical.png",dpi=255)
    fig.savefig(out/"Abell3128_Radio_Optical.pdf",metadata={
        "Title":"Radio emission along the Abell 3128 sightline","Author":"Biswajit Jana"})
    plt.close(fig)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,default=Path("data"))
    parser.add_argument("--vis",type=Path,default=Path("../inputs/arc_VIS.fits"))
    parser.add_argument("--output",type=Path,default=Path("results"))
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    maps = [radio_stats(args.data/f"racs-{tile}.fits") for tile in TILES]
    report = {
        "lens_RA_Dec_deg":[LENS.ra.deg,LENS.dec.deg],
        "arc_RA_Dec_deg":[ARC.ra.deg,ARC.dec.deg],
        "optical_lens_arc_separation_arcsec":LENS.separation(ARC).arcsec,
        "tiles":[item[2] for item in maps],
        "contour_sigma":SIGMAS.tolist(),
        "notes":"Peak values use the brightest native pixel within 30 arcsec. Overlapping mosaics can share data.",
    }
    (args.output/"radio_measurements.json").write_text(json.dumps(report,indent=2)+"\n")
    legacy = image(args.data/"legacy_dr10_r.fits")
    legacy_lens = image(args.data/"legacy_dr10_r_lens.fits")
    euclid = image(args.vis)
    figure(legacy,legacy_lens,euclid,maps[0],report,args.output)


if __name__ == "__main__":
    main()
