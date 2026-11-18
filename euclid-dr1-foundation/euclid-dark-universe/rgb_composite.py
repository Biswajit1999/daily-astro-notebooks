"""Build an RGB visualization of the released DES J0330-5228 FITS mosaics."""
from pathlib import Path
import argparse
import json

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from get_arc_fits import CENTRE


CHANNELS = {"R": ("NIR-H", 0.60), "G": ("VIS", 2.15), "B": ("DES-G", 8.0)}


def composite(inputs, results):
    stacks, channels = [], {}
    wref = None
    center = SkyCoord(*CENTRE, unit="deg")
    for channel, (band, gain) in CHANNELS.items():
        raw, hdr = fits.getdata(inputs / f"arc_{band}.fits", header=True)
        w = WCS(hdr).celestial
        zpt = float(hdr["MAGZERO"])
        if wref is None:
            wref, shape = w, raw.shape
        height, width = shape
        x = [0, 0, width-1, width-1, (width-1)/2]
        y = [0, height-1, 0, height-1, (height-1)/2]
        xy_error = float(w.pixel_to_world(x,y).separation(wref.pixel_to_world(x,y)).arcsec.max())
        if raw.shape != shape or xy_error > .001 or not np.isfinite(raw).all():
            raise ValueError(f"Mismatched or non-finite {band} mosaic")
        xc, yc = w.world_to_pixel(center)
        yy, xx = np.indices(raw.shape)
        off = np.hypot(xx-xc, yy-yc) > 168
        sky = float(np.median(raw[off]))
        # Place all channels on the same AB zero-point scale before display gains.
        stacks.append((raw.astype(float)-sky)*10**(.4*(30-zpt))*gain)
        channels[channel] = {"band":band, "AB_zeropoint":zpt, "sky_offset_native_units":sky,
                             "display_gain":gain, "header_grid_max_separation_arcsec":xy_error}
    stack = np.stack(stacks,axis=-1)
    intensity = np.maximum(stack.mean(axis=-1),0)
    xc,yc = wref.world_to_pixel(center)
    y,x = np.indices(intensity.shape)
    cropped = (abs(x-xc)<=160)&(abs(y-yc)<=160)
    scale = float(np.percentile(intensity[cropped],98.8))
    if scale <= 0:
        raise ValueError("Display normalization must be positive")
    softening = scale/15
    luminance = np.arcsinh(intensity/softening)/np.arcsinh(3*scale/softening)
    factor = np.divide(luminance,intensity,out=np.zeros_like(intensity),where=intensity>0)
    image = np.maximum(stack * factor[:,:,None],0)
    image /= np.maximum(1.,image.max(axis=-1))[:,:,None]
    fig = plt.figure(figsize=(8.0,8.5),facecolor="white")
    ax = fig.add_axes([.06,.102,.88,.827])
    pxscale = float(np.sqrt(np.prod(u.Quantity(wref.proj_plane_pixel_scales()).to_value(u.deg)))*3600)
    limits = ((-.5-xc)*pxscale,(width-.5-xc)*pxscale,(-.5-yc)*pxscale,(height-.5-yc)*pxscale)
    ax.imshow(image,extent=limits,origin="lower",interpolation="nearest")
    ax.set(xlim=(-14.5,14.5),ylim=(-14.5,14.5),xticks=[],yticks=[])
    ax.plot([-12.4,-7.4],[-12.2,-12.2],color="white",lw=2)
    ax.text(-9.9,-11.65,'5″',ha="center",fontsize=11,color="white")
    ax.text(-12.4,12.0,"N ↑  E ←",fontsize=10,color="white")
    fig.text(.073,.978,"Gravitational arc in the Abell 3128 sightline",fontsize=17,
             color="black",weight="bold",va="top")
    fig.text(.073,.074,"DES J0330−5228   |   R  Euclid NISP H   ·   G  Euclid VIS   ·   B  Blanco DECam g",
             fontsize=10,color="#181818")
    fig.text(.073,.046,"Observed-band composite with a shared asinh stretch. Euclid, NASA, ESA and DES/DECam via IRSA.",
             fontsize=8.5,color="#404040")
    fig.text(.073,.022,"Image processing  Biswajit Jana   |   Euclid DR1-Foundation   |   MER tile 102017310",
             fontsize=8.5,color="#404040")
    fig.savefig(results/"Abell3128_RGB.png",dpi=235)
    plt.close(fig)
    summary={"channels":channels,"field_width_arcsec":29.,"pixel_scale_arcsec":float(pxscale),
             "display_method":"Common zero point 30, subjective per-band display gains, shared asinh intensity",
             "scale_in_common_imaging_units":scale,"softening_in_common_imaging_units":softening,
             "photometric_use":"Display only. Band-dependent PSFs were retained."}
    (results/"rgb_display.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path);p.add_argument("results",type=Path)
    a=p.parse_args()
    print(json.dumps(composite(a.inputs,a.results),indent=2))
