"""Conservative one-plane projected mass versus deflector stellar budget."""
from pathlib import Path
from zipfile import ZipFile
import argparse
import hashlib
import json

from astropy.cosmology import Planck18
from astropy import constants as const, units as u
import numpy as np
import pandas as pd


EXPECTED_MD5 = {"eclipse_object.zip":"56433fecbdc459046ffe9eca44bb4dcf",
                "eclipse_physical.zip":"cb31dbd65a3586ab13f52cff2df67f6b"}


def mass(dl_mpc, theta_arcsec, amplification=1.):
    scale = (const.c**2/4/const.G*u.Mpc).to_value(u.Msun)
    return scale * dl_mpc * np.deg2rad(theta_arcsec/3600)**2 * amplification


def budgets(folder):
    for name, md5 in EXPECTED_MD5.items():
        with (folder/name).open("rb") as f:
            if hashlib.file_digest(f,"md5").hexdigest()!=md5:
                raise ValueError(f"Checksum mismatch for {name}")
    columns = ["lens_grade","unique_identifier","eclipse_median_phz","eclipse_min70_phz",
               "eclipse_effective_einstein_radius","eclipse_effective_einstein_radius_lower_1_sigma",
               "eclipse_log_survived_mass_med","eclipse_log_survived_mass_upp",
               "lens_model_success","lens_model_consensus_75","final_sample","ra","dec"]
    with ZipFile(folder/"eclipse_physical.zip") as z:
        name = next(n for n in z.namelist() if "_key_" in n and n.endswith(".csv"))
        t = pd.read_csv(z.open(name),usecols=columns)
    with ZipFile(folder/"eclipse_object.zip") as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        a = pd.read_csv(z.open(name),usecols=["Unique_Identifier","large_system_warning","disc_deflector","desi_deflector_specz"])
    a = a.drop_duplicates("Unique_Identifier")
    t = t.merge(a,left_on="unique_identifier",right_on="Unique_Identifier",how="left",validate="one_to_one")
    row0 = len(t)
    stages = [
        ("A grade", t.lens_grade.eq("A")),
        ("ECLIPSE-D final sample", t.final_sample.eq(True)),
        ("75% model consensus and successful model", t.lens_model_consensus_75.eq("Success")&t.lens_model_success.eq(True)),
        ("no large-system flag or disc flag", t.large_system_warning.eq(False)&t.disc_deflector.eq(False)),
        ("valid distances, radius and stellar mass",
            t.eclipse_median_phz.between(.15,.85)&t.eclipse_min70_phz.between(.10,.85)
            &t.eclipse_effective_einstein_radius_lower_1_sigma.between(.2,5)
            &t.eclipse_effective_einstein_radius.between(.2,5)
            &t.eclipse_effective_einstein_radius_lower_1_sigma.le(t.eclipse_effective_einstein_radius)
            &t.eclipse_log_survived_mass_med.between(10,13)&t.eclipse_log_survived_mass_upp.between(0,1)),
    ]
    good = np.ones(len(t),dtype=bool)
    counts={"input":row0}
    for name, use in stages:
        good &= use.to_numpy(dtype=bool)
        counts[name]=int(good.sum())
    t = t[good].copy()
    z = t.eclipse_median_phz.to_numpy()
    zl = t.eclipse_min70_phz.to_numpy()
    re = t.eclipse_effective_einstein_radius.to_numpy()
    rel = t.eclipse_effective_einstein_radius_lower_1_sigma.to_numpy()
    med = t.eclipse_log_survived_mass_med.to_numpy()
    up = t.eclipse_log_survived_mass_upp.to_numpy()
    t["lg_floor_med"] = np.log10(mass(Planck18.angular_diameter_distance(z).value,re))
    t["lg_floor_low"] = np.log10(mass(Planck18.angular_diameter_distance(zl).value,rel))
    t["lg_excess_med"] = t.lg_floor_med-med
    t["lg_excess_conservative"] = t.lg_floor_low-med-up
    spec = t.desi_deflector_specz.to_numpy(dtype=float)
    matches = np.isfinite(spec)&(spec>=.1)&(spec<=.85)&(np.abs(spec-z) <= .05*(1+z))
    t["specz_agrees"] = matches
    floor = np.full(len(t),np.nan)
    floor[matches] = np.log10(mass(Planck18.angular_diameter_distance(spec[matches]).value,rel[matches]))
    t["lg_excess_specz"] = floor-med-up
    stat = {
        "selection":counts,
        "n_catalogue_lenses":int(len(t)),
        "central_estimate_above_stars":int((t.lg_excess_med>0).sum()),
        "lower_radius_lower_z_upper_stars":int((t.lg_excess_conservative>0).sum()),
        "lower_radius_lower_z_upper_stars_plus_0p30dex":int((t.lg_excess_conservative>.30).sum()),
        "specz_subset":int(matches.sum()),
        "specz_subset_above_stars_plus_0p30dex":int((t.lg_excess_specz>.30).sum()),
        "top3_ids":t.nlargest(3,"lg_excess_conservative").unique_identifier.tolist(),
        "median_radius_arcsec":float(t.eclipse_effective_einstein_radius.median()),
        "radius_interval_10_to_90":t.eclipse_effective_einstein_radius.quantile([.1,.9]).tolist(),
        "median_deflector_z":float(t.eclipse_median_phz.median()),
    }
    return t,stat


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    table,summary=budgets(a.inputs)
    table.to_csv(a.output/"lens_budget.csv",index=False)
    (a.output/"lens_budget.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
