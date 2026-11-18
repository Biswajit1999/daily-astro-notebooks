"""Build registered optical/NIR FITS stamps and query independent archives."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from scipy.ndimage import map_coordinates

from archive import get,image_strip,product,window
from search_doubles import robust

DR10="https://www.legacysurvey.org/viewer/fits-cutout"
MAST="https://mast.stsci.edu/vo-tap/api/v0.1/caom/sync"
GAIA="https://gea.esac.esa.int/tap-server/tap/sync"
SIMBAD="https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
VIZ="https://vizier.cfa.harvard.edu/viz-bin/asu-xml"
IRSA="https://irsa.ipac.caltech.edu/TAP/sync"
NP=161
SCALE=.1


def cone(ra,dec,radius,ac="ra",dc="dec"):
    return f"1=CONTAINS(POINT('ICRS',{ac},{dc}),CIRCLE('ICRS',{ra},{dec},{radius/3600:.9f}))"


def tap(name, endpoint, query, target, count):
    url=endpoint+"?"+urlencode({"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":query})
    result={"endpoint":endpoint,"adql":query}
    try:
        raw=get(url,seconds=17)
        reader=csv.DictReader(io.StringIO(raw.decode()))
        if not reader.fieldnames or reader.fieldnames[0].startswith("<") or len(reader.fieldnames)<2:
            raise ValueError("Response was not the expected TAP CSV")
        rows=list(reader)
        if len(rows)>=count:
            result["row_cap_reached"]=True
        target.joinpath(f"{name}.csv").write_bytes(raw)
        result.update(rows=len(rows),file=f"{name}.csv",sha256=hashlib.sha256(raw).hexdigest(),data=rows)
    except Exception as e:
        result["error"]=str(e)[:320]
    return name,result


def queries(row,folder):
    ra,dec=row["ra"],row["dec"]
    here=cone(ra,dec,6)
    limit=100
    base=[
        ("gaia",GAIA,f"SELECT TOP {limit} source_id,ra,dec,ref_epoch,parallax,parallax_error,"
         f"pmra,pmdec,ruwe,ipd_frac_multi_peak,phot_g_mean_mag FROM gaiadr3.gaia_source WHERE {here}"),
        ("simbad",SIMBAD,f"SELECT TOP {limit} main_id,otype,ra,dec,rvz_redshift,rvz_bibcode FROM basic WHERE {here}"),
        ("mast",MAST,f"SELECT TOP {limit} obs_collection,obs_id,instrument_name,s_ra,s_dec,access_url,s_region "
         f"FROM ivoa.obscore WHERE obs_collection IN ('HST','JWST') AND dataproduct_type='image' AND "
         f"1=INTERSECTS(s_region, CIRCLE('ICRS',{ra},{dec},0.000277778))"),
        ("mer",IRSA,f"SELECT TOP {limit} object_id,ra,dec,tileid,det_quality_flag,flag_vis,flag_j,parent_id,"
         f"flux_vis_2fwhm_aper,flux_j_2fwhm_aper FROM euclid_dr1_mer_catalogue_deep_survey WHERE {cone(ra,dec,2)}"),
    ]
    with ThreadPoolExecutor(max_workers=4) as p:
        result=dict(p.map(lambda entry:tap(*entry,folder,limit),base))
    url=VIZ+"?"+urlencode({"-source":"B/wds/wds","-c":f"{ra} {dec}","-c.rs":15,"-out.max":100})
    record={"query":url}
    try:
        an=get(url,seconds=17)
        root=ET.fromstring(an)
        statuses=[i for i in root.findall(".//{*}INFO") if i.get("name") in ("QUERY_STATUS","Error")]
        if any(x.get("value") not in ("OK","OVERFLOW") for x in statuses):
            raise ValueError("WDS server returned a query error")
        if not root.findall(".//{*}TABLE"):
            raise ValueError("No WDS table returned")
        rows=root.findall(".//{*}TR")
        (folder/"wds.xml").write_bytes(an)
        record.update(rows=len(rows),file="wds.xml")
    except Exception as e:
        record["error"]=str(e)[:320]
    result["wds"]=record
    return result


def target_wcs(row):
    w=WCS(naxis=2)
    w.wcs.crval=[row["ra"],row["dec"]]
    w.wcs.crpix=[(NP+1)/2]*2
    w.wcs.cdelt=[-SCALE/3600,SCALE/3600]
    w.wcs.ctype=["RA---TAN","DEC--TAN"]
    w.wcs.radesys="ICRS"
    return w


def reproject(array, header, origin, w):
    yy,xx=np.indices((NP,NP))
    x,y=WCS(header).celestial.world_to_pixel_values(*w.pixel_to_world_values(xx,yy))
    arr=map_coordinates(array,[y-origin[1],x-origin[0]],order=1,cval=np.nan,prefilter=False)
    return arr


def stamp(row,folder,cache):
    tile=int(row["tile"])
    w=target_wcs(row)
    files,planes={},{}
    for band in ("VIS","J"):
        a,h,meta=image_strip(tile,band,cache)
        planes[band]=reproject(a,h,meta["origin_xy"],w)
        files[band]={"url":meta["url"],"etag":meta["etag"],"unit":meta["unit"]}
    try:
        h, hs, meta=product(tile,"i2")
        x,y=WCS(h).celestial.world_to_pixel_values(row["ra"],row["dec"])
        data,origin,ranges=window((h,hs,meta),x,y,105)
        planes["HSC i2"]=reproject(data,h,origin,w)
        files["HSC i2"]={**meta,"ranges":ranges,"facility":"Subaru/HSC; WISHES image resampled by MER"}
    except Exception as ex:
        files["HSC i2"]={"error":str(ex)[:370]}
    if "HSC i2" not in planes or np.count_nonzero(np.isfinite(planes["HSC i2"]) & (planes["HSC i2"]!=0))<NP**2*.85:
        url=DR10+"?"+urlencode({"ra":row["ra"],"dec":row["dec"],"layer":"ls-dr10","bands":"r",
                                "pixscale":.262,"size":76})
        try:
            raw=get(url)
            with fits.open(io.BytesIO(raw)) as h:
                planes["Legacy r"]=reproject(np.squeeze(h[0].data),h[0].header,(0,0),w)
                files["Legacy r"]={"url":url,"sha256":hashlib.sha256(raw).hexdigest(),
                                   "survey":h[0].header.get("SURVEY"),"release":h[0].header.get("VERSION"),
                                   "facility":"BASS/MzLS northern input; r from Bok/90Prime where covered",
                                   "data_file":"legacy_r_native.fits"}
            (folder/"legacy_r_native.fits").write_bytes(raw)
        except Exception as ex:
            files["Legacy r"]={"url":url,"error":str(ex)[:370]}
    result=analyse_planes(row,w,planes,files,folder)
    return result


def analyse_planes(row,w,planes,files,folder):
    yy,xx=np.indices((NP,NP))
    center=(NP-1)/2
    rr=np.hypot(xx-center,yy-center)
    x,y=w.world_to_pixel_values([row["ra1"],row["ra2"]],[row["dec1"],row["dec2"]])
    # Centroid and shape on the native-band PSF: optically unresolved/extended context only.
    def image_metrics(a):
        valid=np.isfinite(a)&(a!=0)
        ann=(rr>=22)&(rr<=64)&valid
        if ann.sum()<400:
            return {"coverage":float(valid.mean())}
        med,noise=robust(a[ann])
        blank=[]
        for xo in np.arange(14,NP-14,12):
            for yo in np.arange(14,NP-14,12):
                q=(xx-xo)**2+(yy-yo)**2<=36
                if rr[yo,xo]>24 and valid[q].all(): blank.append(a[q].mean())
        measured=[]
        for xp,yp in zip(x,y,strict=True):
            use=((xx-xp)**2+(yy-yp)**2<=36)&valid
            measured.append(float(a[use].mean()) if use.sum() else None)
        ap_med,ap_noise=robust(np.asarray(blank))
        contrast=[(f-ap_med)/ap_noise if f is not None and ap_noise>0 else None for f in measured]
        return {"coverage":float(valid.mean()),"background":med,"pixel_mad_sigma":noise,
                "component_aperture_contrast":contrast,"blank_apertures":len(blank),
                "aperture_diameter_arcsec":1.2}

    hdus=[fits.PrimaryHDU()]
    for n,d in planes.items():
        files[n].update(image_metrics(d))
        h=w.to_header()
        h["ORIGIN"]="Euclid DR1-F / IRSA" if n!="Legacy r" else "Legacy Survey DR10"
        if files[n].get("unit"): h["BUNIT"]=files[n]["unit"]
        hdus.append(fits.ImageHDU(d,h,name=n.replace(" ","_")))
    with gzip.open(folder/"registered.fits.gz","wb") as f:
        fits.HDUList(hdus).writeto(f)
    layout=["VIS","J",next((n for n in ("HSC i2","Legacy r") if n in planes and files[n].get("coverage",0)>.85),"HSC i2")]
    fig,axes=plt.subplots(1,3,figsize=(7.8,2.85),layout="constrained")
    for ax,n in zip(axes,layout,strict=True):
        if n in planes and files[n].get("pixel_mad_sigma",0)>0:
            d=(planes[n]-files[n]["background"])/files[n]["pixel_mad_sigma"]
            ax.imshow(np.arcsinh(d),origin="lower",cmap="gray",vmin=-1,vmax=3.4)
            for xp,yp in zip(x,y,strict=True):
                ax.add_patch(Circle((xp,yp),3.3,fill=False,color="#ffd46e",lw=.85))
        else:
            ax.text(.5,.5,"Coverage unavailable",ha="center",va="center",transform=ax.transAxes,fontsize=9)
            ax.set(xlim=(0,NP),ylim=(0,NP))
        ax.set(xticks=[],yticks=[],title={"VIS":"Euclid VIS","J":"Euclid NISP J"}.get(n,n))
    axes[0].plot([11,41],[13,13],color="white",lw=1.8)
    axes[0].text(26,17,'3″',color="white",ha="center",fontsize=8)
    axes[0].text(10,145,"N ↑   E ←",color="white",fontsize=8)
    fig.suptitle(f"{row['id']}   ·   ICRS {row['ra']:.6f}°, {row['dec']:.6f}°   ·   {row['sep_arcsec']:.2f}″",fontsize=11)
    fig.savefig(folder/"cutouts.webp",dpi=155,pil_kwargs={"quality":87})
    plt.close(fig)
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results",type=Path,default=Path("results"))
    p.add_argument("--cache",type=Path,required=True)
    args=p.parse_args()
    with (args.results/"candidates.csv").open() as f:
        selected=[x for x in csv.DictReader(f) if x["j_state"]=="pass"][:6]
    def one(row):
        for key in ("ra","dec","ra1","ra2","dec1","dec2","sep_arcsec"):
            row[key]=float(row[key])
        f=args.results/"audit"/row["id"]
        f.mkdir(parents=True,exist_ok=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            image=pool.submit(stamp,row,f,args.cache)
            catalogs=pool.submit(queries,row,f)
            return row["id"],{"candidate":row,"images":image.result(),"catalogues":catalogs.result()}
    with ThreadPoolExecutor(max_workers=3) as p:
        data=dict(p.map(one,selected))
    (args.results/"audit.json").write_text(json.dumps(data,indent=2)+"\n")

if __name__=="__main__":
    main()
