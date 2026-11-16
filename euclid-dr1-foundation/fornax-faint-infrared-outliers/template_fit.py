"""Exploratory photon-weighted stellar, galaxy and QSO template fits in flux space."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from astropy import units as u
from astropy.io import fits
from astropy.io.votable import parse_single_table
from dust_extinction.parameter_averages import CCM89
import matplotlib.pyplot as plt
import numpy as np
from speclite.filters import load_filter

Z = np.round(np.arange(0, 3.801, .02), 2)
K = np.log(10)/2.5
EAZY = "https://raw.githubusercontent.com/gbrammer/eazy-photoz/master/templates/CWW%2BKIN"
SPEX = "https://www.cass.ucsd.edu/~ajb/browndwarfs/spexprism/spectra"
PICKLES = "https://ssb.stsci.edu/cdbs/deliveries/etc/trds.24.3xxxx/grid/pickles/dat_uvk"
MODELS = {
    **{f"{n}.dat": (f"{EAZY}/{n}_ext.sed", "galaxy")
       for n in ("CWW_E", "CWW_Sbc", "CWW_Scd", "CWW_Im", "KIN_SB1", "KIN_SB2")},
    "QSO.dat": ("https://raw.githubusercontent.com/jselsing/QuasarComposite/master/Selsing2015_interpolated.dat", "QSO"),
    "T5.dat": (f"{SPEX}/spex-prism_2MASSJ15031961+2525196_20030522_BUR04B.txt", "mid-T"),
    "T6.dat": (f"{SPEX}/spex-prism_SDSSpJ162414.37+002915.6_20040312_BUR06D.txt", "mid-T"),
    **{f"Pickles_{i}.fits": (f"{PICKLES}/pickles_uk_{i}.fits", "star") for i in (5, 30, 40, 48)},
}


def read_inputs(path):
    import requests
    extinction = ET.parse(path / "foreground_dust.xml").findtext(".//refPixelValueSandF")
    ebv = float(extinction.split()[0])
    bands = {}
    for b in ("VIS", "Y", "J", "H"):
        f = load_filter(f"Euclid-{b}")
        bands[f"E.{b}"] = (f.wavelength, f.response)
    for b in ("Z", "Y", "J", "H", "Ks"):
        f = parse_single_table(path / f"VIRCAM_{b}.xml").to_table()
        bands[f"V.{b}"] = (np.asarray(f["Wavelength"], float), np.asarray(f["Transmission"], float))
    templates, records = [], []
    for name, (url, family) in MODELS.items():
        p = path / name
        if not p.exists():
            response = requests.get(url, timeout=24)
            response.raise_for_status()
            p.write_bytes(response.content)
        if p.suffix == ".fits":
            with fits.open(p) as hdus:
                data = hdus[1].data
                wave, flux = data["WAVELENGTH"].astype(float), data["FLUX"].astype(float)
                note = hdus[0].header.get("FILENAME", name)
        else:
            wave, flux = np.loadtxt(p, usecols=(0, 1), unpack=True)
            note = name
        if family == "mid-T":
            wave *= 1e4
        use = np.isfinite(wave) & np.isfinite(flux)
        order = np.argsort(wave[use])
        wave, flux = wave[use][order], flux[use][order]
        templates.append((name, family, wave, flux))
        records.append({"path": name, "family": family, "url": url,
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "label": note})
    return bands, templates, ebv, records


def integrate(wave, flux, redshift, passbands):
    result = []
    for lam, throughput, attenuation in passbands:
        d = np.trapezoid(throughput/lam, lam)
        # Require >99% of response weight to lie within the valid template domain.
        inside = (lam >= (1+redshift)*wave[0]) & (lam <= (1+redshift)*wave[-1])
        if np.trapezoid((throughput/lam)*inside, lam) < .99*d:
            result.append(np.nan)
            continue
        shape = np.interp(lam/(1+redshift), wave, flux, left=0, right=0)
        result.append(np.trapezoid(throughput*shape*attenuation*lam, lam)/d)
    return np.asarray(result)


def observed(t, external):
    result = {}
    for b in ("VIS", "Y", "J", "H"):
        tag = f"{b.lower()}_2fwhm_aper"
        f, e = float(t[f"flux_{tag}"]), float(t[f"fluxerr_{tag}"])
        if np.isfinite(f) and np.isfinite(e) and e > 0 and t[f"flag_{b.lower()}"] == "0":
            result[f"E.{b}"] = (f, e)
    matches = external["VIDEO_CAT_DR5"]["matches"]
    if matches and float(matches[0]["angular_separation_arcsec"]) <= .7:
        row = matches[0]
        for b in ("Z", "Y", "J", "H", "Ks"):
            if row[f"{b.upper()}_FLAGS"] != "0" or "--" in (row[f"{b.upper()}_MAG_APER_3"], row[f"{b.upper()}_MAGERR_APER_3"]):
                continue
            m, e = (float(row[f"{b.upper()}_{x}_APER_3"]) for x in ("MAG", "MAGERR"))
            f = 10**((23.9-m)/2.5)
            if np.isfinite(f) and e > 0:
                result[f"V.{b}"] = (f, K*f*e)
    return result


def profile_intervals(rows, best):
    grid = sorted({row["z"] for row in rows if row["chi2"] <= best+4})
    spans = []
    for z in grid:
        if not spans or z > spans[-1][-1]+.021:
            spans.append([z,z])
        else:
            spans[-1][-1] = z
    return spans


def fit(data, model_grid):
    bands = list(data)
    f, error = np.asarray(list(data.values())).T
    error = np.hypot(error, .05*np.abs(f))
    groups = np.asarray([n.split(".")[0] for n in bands])
    results = []
    for name, family, z, shape in model_grid:
        model = np.asarray([shape[b] for b in bands])
        if not np.isfinite(model).all():
            continue
        predictions = np.zeros(len(f))
        for group in np.unique(groups):
            pick = groups == group
            normalized = model[pick] / np.max(np.abs(model[pick]))
            norm = max(0., np.sum(f[pick]*normalized/error[pick]**2) / np.sum((normalized/error[pick])**2))
            predictions[pick] = norm*normalized
        chi2 = np.sum(((f-predictions)/error)**2)
        results.append({"family": family, "template": name, "z": z, "chi2": float(chi2),
                        "predictions_uJy": predictions.tolist()})
    return results


def plot(out, target, data, result):
    names = list(data)
    f, e = np.asarray(list(data.values())).T
    pos = np.arange(len(f))
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.55), layout="constrained",
                             gridspec_kw={"width_ratios": [1.38, 1]})
    ax = axes[0]
    ax.errorbar(pos, f, yerr=e, fmt="o", color="black", ms=4, label="Observed")
    for family, record in result["full"]["families"].items():
        ax.plot(pos, record["predictions_uJy"], ".-", lw=.9, ms=4, label=family)
    ax.set(xticks=pos, xticklabels=names, ylabel="Flux density (µJy)", title=f"{target} · optical + near-IR")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=7, ncol=2)
    ax = axes[1]
    for family in ("galaxy", "QSO"):
        pts = result["full"]["profiles"].get(family, {})
        if pts:
            ax.plot(list(map(float, pts)), list(pts.values()), label=family)
    ax.axvline(result["phz_median"], color="#52636e", ls="--", lw=1, label="Euclid PHZ median")
    ax.set(xlabel="Trial redshift", ylabel="Profile χ²", title="Limited template library", ylim=(0, None))
    ax.legend(fontsize=7)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=Path("results"), type=Path)
    parser.add_argument("--inputs", default=Path("inputs"), type=Path)
    args = parser.parse_args()
    filter_data, templates, ebv, records = read_inputs(args.inputs)
    laws = CCM89(Rv=3.1)
    names = list(filter_data)
    passbands = [(lam, throughput, laws.extinguish(lam*u.AA, Av=ebv*3.1))
                 for lam, throughput in filter_data.values()]
    grid = [(name, family, float(z), dict(zip(names, integrate(wave, shape, z, passbands), strict=True)))
            for name, family, wave, shape in templates
            for z in (Z if family in ("galaxy","QSO") else [0.])]
    external = json.loads((args.results/"external_audit.json").read_text())["targets"]
    with (args.results/"screen_candidates.csv").open() as f:
        targets = [row for row in csv.DictReader(f) if row["audit_id"]]
    summary = {"foreground_ebv_mag": ebv, "templates": records, "targets": {}}
    for target in targets:
        label = target["audit_id"]
        data = observed(target, external[label])
        result = {"photometry_uJy": data}
        for case in ("near_ir", "full"):
            obs = {b: v for b,v in data.items() if case == "full" or b not in ("E.VIS","V.Z")}
            rows = fit(obs, grid)
            families, profiles = {}, {}
            for family in sorted({r["family"] for r in rows}):
                members = [r for r in rows if r["family"] == family]
                best = min(members, key=lambda r:r["chi2"])
                families[family] = {**best, "delta_chi2_le_4_grid_spans": profile_intervals(members, best["chi2"])}
                profiles[family] = {str(z): min(r["chi2"] for r in members if r["z"] == z)
                                    for z in sorted({r["z"] for r in members})}
            result[case] = {"bands": list(obs), "families": families, "profiles": profiles}
        real = args.results/"audit"/label
        with (real/"phz_photo_z_deep_survey.csv").open() as f:
            result["phz_median"] = float(next(csv.DictReader(f))["phz_median"])
        summary["targets"][label] = result
        plot(real/"template_fit.png", label, data, result)
    (args.results/"template_fits.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    main()
