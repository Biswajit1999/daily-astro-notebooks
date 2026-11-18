"""Measure the published DES J0330-5228 arc in Euclid and DES image cutouts."""
from pathlib import Path
import argparse
import csv
import json

from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates
from scipy.signal import find_peaks

from lens_budget import mass
from get_arc_fits import CENTRE

REFERENCE_ARC = (52.735917,-52.471431)
SOURCE_Z = 1.4541
DEFLECTOR_Z = .44
FOREGROUND_Z = .058
RADII = np.arange(3.8,8.01,.025)
BETWEEN = (4.1,7.9)
PA = np.arange(175.,221.,5.)
BANDS = ("VIS","DES-G","DES-I")
PANEL = ("VIS","DES-G","NIR-H")
LABELS = {"VIS":"Euclid VIS","DES-G":"Blanco DECam g","DES-I":"Blanco DECam i","NIR-H":"Euclid NISP H"}


def stamp(folder, band):
    data, hdr = fits.getdata(folder/f"arc_{band}.fits",header=True)
    return data, WCS(hdr).celestial


def sample(data,w,center,angles,radii):
    a,r=np.meshgrid(angles,radii,indexing="ij")
    world=center.directional_offset_by(a*u.deg,r*u.arcsec)
    x,y=w.world_to_pixel(world)
    return map_coordinates(data,[y,x],order=1,prefilter=False,cval=np.nan)


def profile(data,w,center,angle_grid,control):
    ring=sample(data,w,center,angle_grid,RADII)
    residual=np.nanmedian(ring,axis=0)-np.nanmedian(control,axis=0)
    return gaussian_filter1d(residual,4)


def ridge(data,w,center,angle,width=2.5):
    control=sample(data,w,center,np.arange(-65,125,5),RADII)
    profile_value=profile(data,w,center,np.linspace(angle-width,angle+width,11),control)
    return strongest_ridge(profile_value),profile_value


def strongest_ridge(profile_value):
    index=np.flatnonzero((RADII>=BETWEEN[0])&(RADII<=BETWEEN[1]))
    peaks=find_peaks(profile_value)[0]
    allowed=np.intersect1d(index,peaks)
    if not len(allowed):
        return None
    strongest=allowed[np.argmax(profile_value[allowed])]
    return float(RADII[strongest])


def geometry(z,theta):
    dl=Planck18.angular_diameter_distance(z).value
    ds=Planck18.angular_diameter_distance(SOURCE_Z).value
    dls=Planck18.angular_diameter_distance_z1z2(z,SOURCE_Z).value
    return {"z_deflector":z,"radius_kpc":float(dl*1000*np.deg2rad(theta/3600)),
            "arc_proxy_mass_msun":float(mass(dl,theta,ds/dls))}


def analyse(folder, out):
    center=SkyCoord(*CENTRE,unit="deg")
    arc=SkyCoord(*REFERENCE_ARC,unit="deg")
    measurements, profiles = [], {}
    for band in BANDS:
        data,w=stamp(folder,band)
        profiles[band]=[]
        for angle in PA:
            value,p=ridge(data,w,center,angle)
            profiles[band].append(p)
            measurements.append({"band":band,"pa_deg":float(angle),"arc_ridge_arcsec":value})
    radii={band:np.array([i["arc_ridge_arcsec"] for i in measurements
                          if i["band"]==band and i["arc_ridge_arcsec"] is not None])
           for band in BANDS}
    theta=float(np.median(radii["VIS"]))
    fields=["band","pa_deg","arc_ridge_arcsec"]
    with (out/"arc_ridges.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator="\n")
        writer.writeheader()
        writer.writerows(measurements)
    nearby=geometry(FOREGROUND_Z,theta)
    behind=geometry(DEFLECTOR_Z,theta)
    summary={
        "centre_icrs_deg":CENTRE,"archive_tile":102017310,"source_redshift":SOURCE_Z,
        "reference_arc_centroid_separation_arcsec":float(center.separation(arc).arcsec),
        "reference_arc_centroid_pa_deg":float(center.position_angle(arc).deg),
        "arc_sector_PA_deg":PA.tolist(),
        "per_band":{b:{"sectors":len(radii[b]),"median_arcsec":float(np.median(radii[b])),
                       "sector_range_arcsec":[float(min(radii[b])),float(max(radii[b]))]}
                    for b in radii if len(radii[b])},
        "cluster_redshift_geometry":behind,"foreground_counterfactual":nearby,
        "mass_ratio_background_to_foreground":behind["arc_proxy_mass_msun"]/nearby["arc_proxy_mass_msun"],
        "vis_arc_mass_sector_sensitivity": [geometry(DEFLECTOR_Z,float(t))["arc_proxy_mass_msun"]
                                            for t in (min(radii["VIS"]),max(radii["VIS"]))],
        "published_des_einstein_proxy_arcsec":6.1,"published_des_einstein_proxy_error_arcsec":1.5,
    }
    (out/"arc_geometry.json").write_text(json.dumps(summary,indent=2)+"\n")
    # Same world-coordinate grid across bands. Positive x is west on the displayed grid.
    fig,axs=plt.subplots(1,3,figsize=(10.4,3.9))
    for ax,band in zip(axs,PANEL,strict=True):
        d,w=stamp(folder,band)
        x,y=w.world_to_pixel(center)
        px,py=w.world_to_pixel(arc)
        bg=np.median(d)
        noise=1.4826*np.median(abs(d-bg))
        extent=((-x-.5)*.1,(d.shape[1]-x-.5)*.1,(-y-.5)*.1,(d.shape[0]-y-.5)*.1)
        ax.imshow(np.arcsinh((d-bg)/(3*noise)),extent=extent,origin="lower",
                  interpolation="nearest",cmap="gray",vmin=-.35,vmax=4.55)
        ax.scatter(0,0,marker="+",s=34,linewidths=1.,color="black")
        ax.scatter((px-x)*.1,(py-y)*.1,facecolors="none",edgecolors="white",s=45,linewidths=.9)
        if band in ("VIS","DES-G"):
            found=[r for r in measurements if r["band"]==band and r["arc_ridge_arcsec"] is not None]
            directions=np.deg2rad([r["pa_deg"] for r in found])
            position=np.array([r["arc_ridge_arcsec"] for r in found])
            ax.scatter(-np.sin(directions)*position,np.cos(directions)*position,s=12,
                       facecolors="white",edgecolors="black",linewidths=.45)
        ax.set(xlim=(-11,11),ylim=(-11,11),title=LABELS[band],xticks=[],yticks=[])
        for spine in ax.spines.values(): spine.set_visible(False)
    axs[0].plot([-9,-4],[-9,-9],c="white",lw=2)
    axs[0].text(-6.5,-8.55,'5″',c="white",ha="center",fontsize=8)
    axs[0].text(-10.1,9.4,"N ↑   E ←",c="white",fontsize=8)
    fig.subplots_adjust(left=.03,right=.97,top=.83,bottom=.14,wspace=.07)
    fig.text(.035,.944,"DES J0330−5228 in the Abell 3128 sightline",fontsize=16,fontweight="bold")
    fig.text(.035,.074,"Cross and open ring mark the literature centre and arc centroid. White dots show measured ridge points.",fontsize=8.5)
    fig.text(.035,.035,"Images ESA/Euclid/Euclid Consortium/NASA and DES/DECam via the IRSA MER archive.",fontsize=8,color=".3")
    fig.savefig(out/"Abell3128_Observed_Arc.png",dpi=190)
    plt.close(fig)
    print(json.dumps(summary,indent=2))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    analyse(args.inputs,args.output)
