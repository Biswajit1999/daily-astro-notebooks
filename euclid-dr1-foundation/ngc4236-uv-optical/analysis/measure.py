"""Screen for UV knots and measure local compact VIS excess in NGC 4236."""
import argparse
import csv
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

CENTRE = SkyCoord(184.175492, 69.462569, unit="deg")
PA = np.deg2rad(162)
S = np.sin(PA)
C = np.cos(PA)
OFFSET = CENTRE.skyoffset_frame()


def to_plane(world):
    coord = world.transform_to(OFFSET)
    east = coord.lon.arcsec
    north = coord.lat.arcsec
    return east * S + north * C, east * C - north * S


def from_plane(major, minor):
    return SkyCoord((major*S+minor*C)*u.arcsec, (major*C-minor*S)*u.arcsec, frame=OFFSET).icrs


def mad(image):
    return 1.4826 * np.median(np.abs(image - np.median(image)))


def highpass(image, pixscale, small, large):
    return gaussian_filter(image, small/pixscale) - gaussian_filter(image, large/pixscale)


def outside_optical_ellipse(major, minor):
    return np.hypot(major / 657, minor / 216) > 1


def get_uv(data, outer):
    with fits.open(data/"fuv.fits") as h, fits.open(data/"nuv.fits") as nuv, fits.open(data/"fuv_cov.fits") as cov:
        wcs = WCS(h[0].header)
        uv_xy = wcs.world_to_pixel(CENTRE)
        x0, y0 = map(lambda v: int(round(float(v))), uv_xy)
        half = 435
        sl = np.s_[y0-half:y0+half+1, x0-half:x0+half+1]
        for other in (nuv, cov):
            np.testing.assert_allclose(WCS(other[0].header).world_to_pixel(CENTRE), uv_xy, atol=.01)
        f = h[0].data[sl].astype(float)
        n = nuv[0].data[sl].astype(float)
        e = cov[0].data[sl].astype(float)
        wcs = wcs.slice(sl)
    yy, xx = np.indices(f.shape)
    major, minor = to_plane(wcs.pixel_to_world(xx, yy))
    search = (abs(major)<=480) & (abs(minor)>=60) & (abs(minor)<=180) & (e>500)
    if outer:
        search = (abs(major) <= 480) & (abs(minor) <= 270) & outside_optical_ellipse(major, minor) & (e > 500)
    sky = (abs(major)<480) & (abs(minor)>180) & (abs(minor)<320) & (e>500)
    filtered_f = highpass(f, 1.5, 1.8, 12)
    filtered_n = highpass(n, 1.5, 1.8, 12)
    fstd, nstd = mad(filtered_f[sky]), mad(filtered_n[sky])
    maxima = (maximum_filter(filtered_f,size=9)==filtered_f) & search & (filtered_f>=5*fstd)
    yy, xx = np.where(maxima)
    seeds=[]
    for x,y in zip(xx,yy,strict=True):
        near = np.hypot(*np.mgrid[-2:3,-2:3]) <= 2
        nscore = filtered_n[y-2:y+3,x-2:x+3][near].max()/nstd
        if nscore>=3:
            pos=wcs.pixel_to_world(x,y).icrs
            seeds.append(dict(ra_deg=pos.ra.deg,dec_deg=pos.dec.deg,major_arcsec=major[y,x],minor_arcsec=minor[y,x],
                              fuv_score=filtered_f[y,x]/fstd,nuv_score=nscore))
    seeds.sort(key=lambda row:row["fuv_score"],reverse=True)
    return seeds,wcs,f,filtered_f,search,{"FUV_filtered_sky_MAD":fstd,"NUV_filtered_sky_MAD":nstd,"FUV_peaks":len(xx)}


def optical_score(science, flags, wcs, pos):
    x,y=map(float,wcs.world_to_pixel(pos))
    ix,iy=int(np.rint(x)),int(np.rint(y))
    h=51
    if ix<h or iy<h or ix+h>=science.shape[1] or iy+h>=science.shape[0]:
        return None
    sl=np.s_[iy-h:iy+h+1,ix-h:ix+h+1]
    image=science.section[sl].astype(float)
    quality=flags.section[sl]
    yy,xx=np.indices(image.shape)
    distance=np.hypot(xx+ix-h-x,yy+iy-h-y)*.1
    good=np.isfinite(image)&((quality&1)==0)
    if good[distance<=5].mean()<.9:
        return None
    fill=np.where(good,image,np.median(image[good]))
    smooth=gaussian_filter(fill,1.5)
    ring=(distance>=3)&(distance<=5)&good
    scatter=mad(smooth[ring])
    if scatter<=0:
        return None
    core=(distance<=2)&good
    iy_peak,ix_peak=np.unravel_index(np.argmax(np.where(core,smooth,-np.inf)),smooth.shape)
    score=(smooth[iy_peak,ix_peak]-np.median(smooth[ring]))/scatter
    peak = wcs.pixel_to_world(ix - h + ix_peak, iy - h + iy_peak).icrs
    return float(score),float(distance[iy_peak,ix_peak]),image,good,peak


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--outer", action="store_true", help="Exploratory selection outside the literature D25 ellipse")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    seeds,uv_wcs,uv,filt,search,summary=get_uv(args.data, args.outer)
    all_positions=np.array([(s["major_arcsec"],s["minor_arcsec"]) for s in seeds])
    panels=[]
    with fits.open(args.data/"vis.fits",memmap=True) as sc, fits.open(args.data/"vis_flag.fits",memmap=True) as fl:
        sci,flag=sc[0],fl[0]
        wcs=WCS(sci.header)
        np.testing.assert_allclose(wcs.world_to_pixel(CENTRE),WCS(flag.header).world_to_pixel(CENTRE),atol=.01)
        for idx, row in enumerate(seeds,1):
            row["id"]=idx
            along=row["major_arcsec"]
            heights=row["minor_arcsec"]
            pos=from_plane(along,heights)
            res=optical_score(sci,flag,wcs,pos)
            controls=[]
            for offset in (-45,-30,-15,15,30,45):
                shifted=along+offset
                if abs(shifted)>480 or min(np.hypot(all_positions[:,0]-shifted,all_positions[:,1]-heights))<8:
                    continue
                if args.outer and not outside_optical_ellipse(shifted, heights):
                    continue
                value=optical_score(sci,flag,wcs,from_plane(shifted,heights))
                if value is not None:
                    controls.append(value[0])
            row["outside_d25"] = bool(outside_optical_ellipse(along, heights))
            row["controls_n"]=len(controls)
            row["control_scores"]=",".join(f"{v:.6g}" for v in controls)
            row["vis_score"]=None if res is None else res[0]
            row["peak_offset_arcsec"]=None if res is None else res[1]
            row["control_median"]=float(np.median(controls)) if controls else None
            row["fraction_at_least_as_high"]=(1+sum(v>=res[0] for v in controls))/(1+len(controls)) if res and controls else None
            if res and len(panels)<4:
                panels.append((row,res[2],res[3]))
    measured=[s for s in seeds if s["vis_score"] is not None and s["controls_n"]>=3]
    differences=[s["vis_score"]-s["control_median"] for s in measured]
    above = sum(d > 0 for d in differences)
    summary["selection"] = "outside_d25" if args.outer else "projected_midplane_strips"
    summary["measured_outside_d25"] = sum(row["outside_d25"] for row in measured)
    summary["sky_cells"] = []
    for side in (-1, 1):
        for low in (-480, -240, 0, 240):
            sector = [row for row in measured if low <= row["major_arcsec"] < low + 240
                      and np.sign(row["minor_arcsec"]) == side]
            summary["sky_cells"].append({"minor_side": side, "major_lower_arcsec": low,
                                          "n": len(sector), "above_control_median": sum(
                                              row["vis_score"] > row["control_median"] for row in sector)})
    summary.update({"uv_knots":len(seeds),"usable_vis_with_at_least_3_controls":len(measured),
                    "above_control_median":above,
                    "above_every_control":sum(s["fraction_at_least_as_high"]==1/(1+s["controls_n"]) for s in measured),
                    "median_excess_over_control_statistic":float(np.median(differences)) if differences else None})
    if seeds:
        with (args.output/"knots.csv").open("w") as stream:
            writer=csv.DictWriter(stream,fieldnames=seeds[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(seeds)
    (args.output/"results.json").write_text(json.dumps(summary,indent=2)+"\n")
    fig=plt.figure(figsize=(8.3,6.8),layout="constrained")
    grid=fig.add_gridspec(2,4,height_ratios=[3,1])
    sky=fig.add_subplot(grid[0,:],projection=uv_wcs)
    lo,hi=np.nanpercentile(uv,[40,99.85])
    sky.imshow(np.arcsinh(np.maximum(uv-lo,0)/(hi-lo)*8),cmap="gray",origin="lower")
    theta = np.linspace(0, 2 * np.pi, 300)
    px, py = uv_wcs.world_to_pixel(from_plane(657 * np.cos(theta), 216 * np.sin(theta)))
    sky.plot(px, py, color="#9af1bc", lw=1, ls="--")
    for minor in (() if args.outer else ((60,180),(-180,-60))):
        px,py=uv_wcs.world_to_pixel(from_plane(np.array([-480,480,480,-480]),np.array([minor[0],minor[0],minor[1],minor[1]])))
        sky.add_patch(Polygon(np.array([px,py]).T,fill=False,linestyle=":",color="#82d3ee"))
    illustrated = {row["id"] for row, _, _ in panels}
    for row in seeds:
        x,y=uv_wcs.world_to_pixel_values(row["ra_deg"],row["dec_deg"])
        sky.scatter(x,y,s=17,facecolor="none",edgecolor="#ffd277",lw=.8)
        if row["id"] in illustrated:
            sky.text(x+12,y+10,str(row["id"]),color="#ffd277",fontsize=9)
    sky.set(xlim=(55,815),ylim=(50,820),title="NGC 4236 · GALEX FUV")
    sky.coords[0].set_axislabel("Right ascension (ICRS)")
    sky.coords[1].set_axislabel("Declination (ICRS)")
    for col,(row,im,good) in enumerate(panels):
        ax=fig.add_subplot(grid[1,col])
        lo,hi=np.percentile(im[good],[25,99.6])
        ax.imshow(np.arcsinh(5*(im-lo)/(hi-lo)),cmap="gray",origin="lower")
        ax.add_patch(plt.Circle((51,51),20,fill=False,color="#ffd277",lw=.85))
        ax.plot([6,16],[7,7],c="white",lw=1.4)
        ax.set(xticks=[],yticks=[],title=f"Euclid VIS · {row['id']}")
    fig.savefig(args.output/"ngc4236_uv_vis.png",dpi=170)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
