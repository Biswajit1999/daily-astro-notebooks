"""Stress-test arc extraction, stellar budgets and the DESI acceleration profile."""
from itertools import product
from pathlib import Path
import argparse
import json

from astropy import units as u
from astropy.coordinates import SkyCoord
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import brentq, minimize_scalar

from arc_geometry import CENTRE, PA, RADII, geometry, sample, stamp, strongest_ridge
from bao import fit, profile_function


CONTROLS = {"baseline": np.arange(-65,125,5),
            "north_east": np.arange(-40,100,5),
            "north_west": np.arange(-100,60,5)}
SMOOTHING_ARCSEC = (.05,.10,.20)
DEFLECTOR_Z = (.42,.44,.46)


def arc_sweep(inputs, results):
    original = json.loads((results/"arc_geometry.json").read_text())
    center = SkyCoord(*CENTRE, unit="deg")
    offsets = [(0.,0.)] + [(d,a) for d in (.1,.25) for a in range(0,360,45)]
    angles = PA[:,None]+np.linspace(-2.5,2.5,11)
    rows = []
    for band in ("VIS","DES-G"):
        image,wcs=stamp(inputs,band)
        for offset,bearing in offsets:
            c=center.directional_offset_by(bearing*u.deg,offset*u.arcsec)
            values=sample(image,wcs,c,angles.ravel(),RADII).reshape(len(PA),11,len(RADII))
            arc=np.nanmedian(values,axis=1)
            for name,az in CONTROLS.items():
                control=np.nanmedian(sample(image,wcs,c,az,RADII),axis=0)
                profiles=arc-control[None,:]
                for smooth in SMOOTHING_ARCSEC:
                    profiles_smooth=gaussian_filter1d(profiles,smooth/(RADII[1]-RADII[0]),axis=1)
                    ridges=[strongest_ridge(x) for x in profiles_smooth]
                    for subset,picked in (("all",ridges),("trimmed",ridges[1:-1])):
                        radii=np.array([x for x in picked if x is not None],dtype=float)
                        rows.append({"band":band,"offset_arcsec":offset,
                                     "offset_pa_deg":bearing,"control":name,
                                     "smoothing_sigma_arcsec":smooth,"sectors":subset,
                                     "usable_sectors":len(radii),
                                     "median_radius_arcsec":float(np.median(radii)) if len(radii) else np.nan})
    table=pd.DataFrame(rows)
    table.to_csv(results/"arc_sensitivity.csv",index=False)
    summaries={}
    for band,group in table.groupby("band"):
        baseline=group[(group.offset_arcsec==0)&group.control.eq("baseline")
                       &(group.smoothing_sigma_arcsec==.10)&group.sectors.eq("all")].iloc[0]
        if not np.isclose(baseline.median_radius_arcsec,original["per_band"][band]["median_arcsec"]):
            raise ValueError(f"Mis-matched baseline for {band}")
        used=group[group.usable_sectors>=6].median_radius_arcsec
        edge=[float(used.min()),float(used.max())]
        masses=[geometry(z,v)["arc_proxy_mass_msun"] for z,v in product(DEFLECTOR_Z,edge)]
        summaries[band]={"tried":len(group),"usable":len(used),"median_range_arcsec":edge,
                         "one_plane_mass_range_msun":[min(masses),max(masses)]}
    return {"band_results":summaries,"deflector_redshifts":DEFLECTOR_Z,
            "note":"Extraction and redshift sensitivity grid. Common imaging data and correlated sectors."}


def stellar_grid(results):
    t=pd.read_csv(results/"lens_budget.csv")
    dex_steps=(0.,.1,.2,.3,.4,.5)
    rows=[]
    for dex,kappa,gas in product(dex_steps,(0.,.10,.20),(0.,.25,.50)):
        offset=dex+np.log10(1+gas)-np.log10(1-kappa)
        rows.append({"stellar_extra_dex":dex,"external_kappa":kappa,"gas_over_enlarged_stellar":gas,
                     "photz_count":int((t.lg_excess_conservative>offset).sum()),
                     "specz_count":int((t.lg_excess_specz>offset).sum())})
    table=pd.DataFrame(rows)
    table.to_csv(results/"stellar_sensitivity.csv",index=False)

    def count(dex,kappa,gas):
        r=table[np.isclose(table.stellar_extra_dex,dex)&np.isclose(table.external_kappa,kappa)
                &np.isclose(table.gas_over_enlarged_stellar,gas)].iloc[0]
        return int(r.photz_count)

    return {"sample":len(t),"specz_overlap":int(t.specz_agrees.sum()),
            "all_at_0p30dex":count(.3,0,0),"joint_stress_at_0p30dex":count(.3,.1,.25),
            "overlap_photz_above_0p30dex":int((t.specz_agrees&(t.lg_excess_conservative>.30)).sum()),
            "overlap_specz_above_0p30dex":int((t.lg_excess_specz>.30).sum()),
            "note":"Uniform external mass sheet and assumed gas budgets are illustrations. Neither is fitted."}


def geometry_profile(profile, q0):
    # Under Lambda-CDM, Omega_Lambda = Omega_m/2 - q0.
    lower=max(.0001,2*q0,q0/1.5)
    upper=min(2.,(2.2+q0)/1.5)
    if lower > upper:
        return float("inf")
    def objective(om):
        return profile(om,1+q0-1.5*om)[0]
    trials=np.linspace(lower,upper,32)
    values=np.array([objective(x) for x in trials])
    at=int(np.argmin(values))
    left,right=trials[max(0,at-1)],trials[min(len(trials)-1,at+1)]
    if not np.isfinite(values[at]) or left == right:
        return float(values[at])
    best=minimize_scalar(objective,bounds=(left,right),method="bounded",options={"xatol":1e-11})
    return float(min(best.fun,values[at]))


def bao_checks(inputs,results):
    mean=np.loadtxt(inputs/"bao_mean.txt",dtype=[("z","f8"),("obs","f8"),("tag","U15")])
    cov=np.loadtxt(inputs/"bao_cov.txt")
    full=json.loads((results/"bao_fits.json").read_text())["full"]
    q_full=full["curved_lambda"]["q0"]
    chi=full["curved_lambda"]["chi2"]
    f=profile_function(mean,cov)
    if not np.isclose(geometry_profile(f,q_full),chi,atol=1e-7):
        raise ValueError("Profile minimum disagrees with direct curved fit")
    if not np.isclose(geometry_profile(f,0.),full["curved_nonaccelerating_lambda"]["chi2"],atol=1e-6):
        raise ValueError("q0 boundary disagrees with constrained two-variable fit")
    roots={}
    for label,dchi in [("delta1",1.),("delta3p84",3.84)]:
        crossing=lambda q:geometry_profile(f,q)-chi-dchi
        roots[label]=[float(brentq(crossing,-.9,q_full)),float(brentq(crossing,q_full,0.))]
    grid=np.sort(np.unique(np.r_[np.linspace(-.83,.025,150),q_full,0.]))
    p=pd.DataFrame({"q0":grid,"delta_chi2":[geometry_profile(f,q)-chi for q in grid]})
    p.to_csv(results/"bao_q0_profile.csv",index=False)
    reduced=[]
    for z in np.unique(mean["z"]):
        mask=mean["z"]!=z
        r=fit(mean,cov,mask)
        best=r["curved_lambda"]
        decel=r["curved_nonaccelerating_lambda"]
        reduced.append({"omitted_redshift":float(z),"retained":int(mask.sum()),"q0":best["q0"],
                        "curved_chi2":best["chi2"],"delta_chi2_nonaccel":decel["chi2"]-best["chi2"]})
    order=pd.DataFrame(reduced)
    order.to_csv(results/"bao_leave_one_redshift.csv",index=False)
    return {"q0_curved":q_full,"profile_ranges":roots,
            "leave_one_q0_range":[float(order.q0.min()),float(order.q0.max())],
            "leave_one_delta_range":[float(order.delta_chi2_nonaccel.min()),
                                     float(order.delta_chi2_nonaccel.max())]}


def plot(results):
    prof=pd.read_csv(results/"bao_q0_profile.csv")
    leave=pd.read_csv(results/"bao_leave_one_redshift.csv")
    fig,ax=plt.subplots(1,2,figsize=(10,3.65),layout="constrained")
    ax[0].plot(prof.q0,prof.delta_chi2,color=".1",linewidth=1.7)
    for y in [1,3.84]:
        ax[0].axhline(y,color=".55",linestyle="--",lw=.8)
    ax[0].set(xlim=(-.76,-.30),ylim=(0,12),xlabel="Present deceleration parameter $q_0$",
              ylabel=r"$\Delta\chi^2$",title="Curved ΛCDM profile")
    ax[1].plot(leave.omitted_redshift,leave.q0,"o-",color=".2",markersize=4)
    ax[1].set(xlabel="Omitted BAO redshift",ylabel="Best-fit $q_0$",title="Omit one redshift at a time")
    for a in ax:
        a.grid(alpha=.16)
        a.spines[["top","right"]].set_visible(False)
    fig.savefig(results/"DESI_BAO_Robustness.png",dpi=185)
    plt.close(fig)


def analyse(inputs,results):
    summary={"arc":arc_sweep(inputs,results),"stellar":stellar_grid(results),
             "bao":bao_checks(inputs,results)}
    (results/"robustness.json").write_text(json.dumps(summary,indent=2)+"\n")
    plot(results)
    return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path); p.add_argument("results",type=Path)
    a=p.parse_args()
    print(json.dumps(analyse(a.inputs,a.results),indent=2))
