"""Fit public optical and near-IR templates to the flagged MER aperture fluxes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from astropy import units as u
from astropy.io import fits
from dust_extinction.parameter_averages import CCM89
import numpy as np
from speclite.filters import load_filter

from archive import get

EAZY="https://raw.githubusercontent.com/gbrammer/eazy-photoz/master/templates/CWW%2BKIN/"
PICKLES="https://ssb.stsci.edu/cdbs/deliveries/etc/trds.24.3xxxx/grid/pickles/dat_uvk/"
DUST="https://irsa.ipac.caltech.edu/cgi-bin/DUST/nph-dust"
MODELS={
    **{f"{n}.dat": (f"{EAZY}{n}_ext.sed","galaxy")
       for n in ("CWW_E","CWW_Sbc","CWW_Scd","CWW_Im","KIN_SB1","KIN_SB2")},
    "QSO.dat":("https://raw.githubusercontent.com/jselsing/QuasarComposite/master/Selsing2015_interpolated.dat","QSO"),
    **{f"Pickles_{i}.fits":(f"{PICKLES}pickles_uk_{i}.fits","star") for i in (5,30,40,48)},
}
FILTERS={"G_EXT_HSC":"hsc2017-g","Z_EXT_HSC":"hsc2017-z","VIS":"Euclid-VIS",
         "Y":"Euclid-Y","J":"Euclid-J","H":"Euclid-H"}


def model(path,details):
    source,family=details
    if not path.exists(): path.write_bytes(get(source,22))
    if path.suffix==".fits":
        with fits.open(path) as f:
            wave=np.array(f[1].data["WAVELENGTH"],float)
            flux=np.array(f[1].data["FLUX"],float)
    else:
        wave,flux=np.loadtxt(path,usecols=(0,1),unpack=True)
    i=np.argsort(wave)
    return wave[i],flux[i],{"input":path.name,"url":source,"family":family,
                           "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def dust(ra,dec):
    url=DUST+"?"+urlencode({"locstr":f"{ra} {dec} equ J2000"})
    raw=get(url,18)
    ebv=float(ET.fromstring(raw).findtext(".//refPixelValueSandF").split()[0])
    return ebv,{"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"ebv":ebv},raw


def fit_basis(templates,passbands,ebv):
    out=[]
    ccm=CCM89(Rv=3.1)
    attenuated=[]
    for f in passbands:
        w,t=f.wavelength,f.response
        attenuated.append((w,t,ccm.extinguish(w*u.AA,Ebv=ebv)))
    for w,f,m in templates:
        zgrid=np.arange(191)*.02 if m["family"]!="star" else [0.]
        for z in zgrid:
            band_vals=[]
            for wave,response,ext in attenuated:
                denom=np.trapezoid(response/wave,wave)
                wr=wave/(1+z)
                covered=(wr>=w[0])&(wr<=w[-1])
                if np.trapezoid(response/wave*covered,wave)<.99*denom:
                    band_vals.append(np.nan)
                    continue
                xx=np.interp(wr,w,f,left=0,right=0)
                band_vals.append(np.trapezoid(wave*response*ext*xx,wave)/denom)
            out.append((m["family"],m["input"],round(float(z),2),np.asarray(band_vals)))
    return out


def profile(rows,delta=4):
    z=sorted({r[1] for r in rows if r[0]<=min(rows)[0]+delta})
    spans=[]
    for x in z:
        if not spans or x>spans[-1][1]+.021: spans.append([x,x])
        else: spans[-1][1]=x
    return spans


def fit(row,basis):
    flux=[]; err=[]
    for band in FILTERS:
        use=(f"FLUX_{band}_2FWHM_APER",f"FLUXERR_{band}_2FWHM_APER")
        a,e=[row.get(k) for k in use]
        usable=a is not None and e is not None and 0<e<1e4 and abs(a)<1e4
        flux.append(a if usable else np.nan); err.append(e if usable else np.nan)
    y,s=np.array(flux),np.array(err); good=np.isfinite(y)&np.isfinite(s)
    if good.sum()<5:
        return {"state":"insufficient_bands","bands":int(good.sum())}
    out={}
    for floor in (.10,.20):
        v,e=y[good],np.hypot(s[good],floor*abs(y[good]))
        result={}
        for group,name,z,m in basis:
            m=m[good]
            if not np.isfinite(m).all() or m.max()<=0:
                continue
            m=m/m.max()
            a=max(0.,float(np.sum(v*m/e**2)/np.sum((m/e)**2)))
            chi=float(np.sum(((v-a*m)/e)**2))
            result.setdefault(group,[]).append((chi,z,name))
        out[str(floor)]={key:{"chi2":min(r)[0],"best_z":min(r)[1],
                            "template":min(r)[2],"delta_chi2_grid_spans":profile(r)}
                         for key,r in result.items()}
    return {"bands":[k for k,o in zip(FILTERS,good,strict=True) if o],"fits":out}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--results",type=Path,default=Path("results"))
    args=p.parse_args()
    args.inputs.mkdir(exist_ok=True,parents=True)
    cat=json.loads((args.results/"euclid_catalogues.json").read_text())
    atlas=[model(args.inputs/n,info) for n,info in MODELS.items()]
    filt=[load_filter(k) for k in FILTERS.values()]
    def one(kv):
        name,r=kv
        try:
            m=r["MER"]
            ebv,meta,raw=dust(m[0]["ra_deg"],m[0]["dec_deg"])
            (args.results/"audit"/name/"foreground_dust.xml").write_bytes(raw)
            basis=fit_basis(atlas,filt,ebv)
            return name,{"dust":meta,"fits":{str(x["OBJECT_ID"]):fit(x,basis) for x in m}}
        except Exception as e:
            return name,{"error":str(e)[:370]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=dict(pool.map(one,cat["targets"].items()))
    (args.results/"photometry_checks.json").write_text(json.dumps({"models":[r[2] for r in atlas],
           "passbands":FILTERS,"targets":result},indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
