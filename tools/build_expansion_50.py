"""Generate fifteen additional dense notebooks for the 50-notebook milestone."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-07-31"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


IMPORTS = """
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

RNG = np.random.default_rng(1999)
plt.style.use("seaborn-v0_8-whitegrid")
COLORS = {"navy":"#071426", "blue":"#1797c9", "cyan":"#2fc6b4",
          "gold":"#f4b942", "orange":"#ef6a45", "rose":"#ce4f78"}
"""


CONTRACT = """
## Analysis contract

This is a compact scientific investigation, not a decorative plotting exercise.
The input is a preserved subset of a public astronomical archive. The notebook
records the upstream table or product, explains every quality cut, prints the
sample size after filtering, reports a numerical result with uncertainty, and
changes at least one defensible analysis choice to test robustness.

Archive catalogue values are heterogeneous measurements collected from the
literature or survey pipelines. A trend in this notebook is therefore a trend
in the selected archive sample, not automatically an occurrence rate, causal
relation, or complete census of nature. Display images are treated as image
arrays rather than calibrated photometry. Spectral equivalent widths identify
relative line strength but do not become elemental abundances without an
atmosphere model.

The small CSV or image already stored in this repository is used so the checked
notebook can be rerun offline. Its provenance remains the original archive; the
local copy is not a new survey release. Random resampling uses a fixed seed so
the uncertainty check is repeatable.
"""


OUTRO = """
## Reading the result responsibly

The primary number answers the stated question only for the documented sample
and method. The stress test asks whether a reasonable threshold change reverses
the conclusion. Agreement does not remove shared selection effects, calibration
limits, unresolved multiplicity, or missing catalogue fields. Disagreement is
reported rather than hidden. A publishable follow-up would repeat the query
against a pinned archive release, model the survey selection function, and use
the original calibrated products where available.

The notebook deliberately separates observation, calculation, interpretation,
and limitation. That makes it useful as a learning record and makes each claim
easy for another reader to audit.

Numerical precision in the printed summary follows the scale supported by this
exercise; extra decimal places would not create extra physical accuracy. The
saved figure exposes the distribution behind the headline value, while the
machine-readable result file lets the dashboard report the finding without
scraping prose. Readers should inspect the executed cells before reusing any
number in a wider scientific argument.
"""


REFERENCES = {
    "exoplanet-archive": """
## Sources and comparison literature

- NASA Exoplanet Archive, TAP guide: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- Planetary Systems table definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
- Winn & Fabrycky (2015), *The Occurrence and Architecture of Exoplanetary Systems*: https://arxiv.org/abs/1410.4199
- Fulton et al. (2017), *A Gap in the Radius Distribution of Small Planets*: https://arxiv.org/abs/1703.10375

The literature provides physical context and expected population structure. It
does not make this heterogeneous archive selection complete or unbiased.
""",
    "sdss": """
## Sources and comparison literature

- SDSS data access and acknowledgement: https://www.sdss.org/science/
- Kewley et al. (2001), theoretical extreme-starburst boundary: https://arxiv.org/abs/astro-ph/0106324
- Kauffmann et al. (2003), empirical BPT separation: https://arxiv.org/abs/astro-ph/0304239
- Pettini & Pagel (2004), N2 and O3N2 abundance indicators: https://arxiv.org/abs/astro-ph/0401128

Strong-line calibrations carry systematic differences that are larger than a
bootstrap interval on the median. Results remain on the named calibration.
""",
    "gaia": """
## Sources and comparison literature

- ESA Gaia Archive: https://gea.esac.esa.int/archive/
- Gaia Collaboration (2023), Gaia Data Release 3 summary: https://doi.org/10.1051/0004-6361/202243940
- Lindegren et al. (2021), Gaia EDR3 astrometric solution: https://arxiv.org/abs/2012.03380
- Gaia Collaboration (2018), cluster kinematics and dynamics: https://arxiv.org/abs/1804.09378

Formal catalogue errors do not include every spatially correlated systematic.
The deconvolved cluster widths are therefore conservative diagnostics.
""",
    "mast": """
## Sources and comparison literature

- MAST data acknowledgement and citation guidance: https://archive.stsci.edu/publishing/
- STIS Data Handbook: https://hst-docs.stsci.edu/stisdhb
- STIS flux and wavelength accuracy limits: https://hst-docs.stsci.edu/stisdhb/chapter-4-stis-error-sources/4-3-factors-limiting-flux-and-wavelength-accuracy

The spectrum is a calibrated STIS product. The M87 JPEG is explicitly treated
as a display preview; physical photometry requires calibrated FITS data, WCS,
exposure information, and point-spread-function treatment.
""",
}


def make_case(archive: str, slug: str, title: str, question: str, source: str,
              topic: str, cells: list[str], figure: str) -> None:
    folder = ROOT / archive / f"{DATE}-{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    intro = f"""
# {title}

**Date:** {DATE}  
**Scientific question:** {question}  
**Preserved source:** `{source}`

{topic}
"""
    notebook = nbf.v4.new_notebook(
        cells=[
            md(intro),
            md(CONTRACT),
            code(IMPORTS),
            *[code(x.replace("{{", "{").replace("}}", "}")) for x in cells],
            md(OUTRO),
            md(REFERENCES[archive]),
        ],
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "colab": {"provenance": []},
        },
    )
    nbf.write(notebook, folder / "notebook.ipynb")
    readme = f"""# {title}

**Question:** {question}

This executed notebook uses the real public-archive subset preserved at
`{source}`. It includes quality control, a numerical measurement, uncertainty,
a robustness check, interpretation, and explicit limits.

![Main result]({figure})

[Open the executed notebook](notebook.ipynb) · [Machine-readable result](result.json)

The notebook ends with archive documentation and comparison literature used to
frame the physical interpretation and its limits.
"""
    (folder / "README.md").write_text(readme, encoding="utf-8")


def exoplanet_cases() -> None:
    source_g = "../2026-07-31-hot-jupiter-tidal-circularisation/giant_planet_archive_query.csv"
    source_t = "../2026-07-31-exoplanet-radius-valley/confirmed_transiting_planets.csv"

    make_case("exoplanet-archive", "exoplanet-discovery-method-timeline",
      "How exoplanet discovery methods changed with time",
      "How did the archive share of major discovery methods change between early and recent discoveries?",
      source_g,
      """The archive records discovery year and method for confirmed planets. We compare
      broad time bins and quantify the change in the leading method. These are catalogue
      counts, not occurrence rates: telescope lifetimes, target selection, follow-up, and
      confirmation policy all shape the timeline. The result is useful as a history of the
      observed sample rather than a statement about the Galaxy's underlying planets.

      Data documentation: NASA Exoplanet Archive Planetary Systems table definitions and
      TAP guide. The composite-style table is convenient for population summaries but can
      combine parameters from different references, so only discovery metadata are used.
      """,
      [f"""
data = pd.read_csv("{source_g}").drop_duplicates("pl_name")
sample = data.dropna(subset=["disc_year", "discoverymethod"]).copy()
sample["disc_year"] = sample.disc_year.astype(int)
sample = sample[sample.disc_year.between(1990, 2026)]
print(f"Unique planets with year and method: {{len(sample):,}}")
print(sample.discoverymethod.value_counts().head(8))
""", """
top = sample.discoverymethod.value_counts().head(5).index
sample["method_group"] = sample.discoverymethod.where(sample.discoverymethod.isin(top), "Other")
bins = [1989, 2005, 2010, 2015, 2020, 2026]
labels = ["1990–05", "2006–10", "2011–15", "2016–20", "2021–26"]
sample["era"] = pd.cut(sample.disc_year, bins=bins, labels=labels)
counts = pd.crosstab(sample.era, sample.method_group)
fractions = counts.div(counts.sum(axis=1), axis=0)
early = sample[sample.disc_year <= 2010].discoverymethod.value_counts(normalize=True)
recent = sample[sample.disc_year >= 2021].discoverymethod.value_counts(normalize=True)
lead_recent = recent.index[0]; lead_share = float(recent.iloc[0])
print(f"Recent leading method: {{lead_recent}} ({{lead_share:.1%}})")
print(fractions.round(3))
""", """
ax = fractions.plot(kind="bar", stacked=True, figsize=(11,5.5), colormap="tab20c")
ax.set(xlabel="Discovery era", ylabel="Fraction of archived discoveries",
       title="Discovery methods represented in the confirmed-planet archive")
ax.legend(title="Method", bbox_to_anchor=(1.02,1), loc="upper left")
plt.tight_layout(); plt.savefig("discovery_method_timeline.png", dpi=180); plt.show()
""", """
# Stress test: move the recent boundary from 2021 to 2019.
recent_alt = sample[sample.disc_year >= 2019].discoverymethod.value_counts(normalize=True)
alt_method, alt_share = recent_alt.index[0], float(recent_alt.iloc[0])
stable = alt_method == lead_recent
print(f"Boundary ≥2019: {{alt_method}} at {{alt_share:.1%}}; same leader={{stable}}")
""", """
result = {"id":"2026-07-31-exoplanet-discovery-method-timeline","title":"Exoplanet discovery methods through time","archive":"NASA Exoplanet Archive","date":"2026-07-31","question":"How has the discovery-method mix changed?","sample_size":int(len(sample)),"results":[f"{{len(sample):,}} unique planets with method and year",f"{{lead_recent}} contributes {{lead_share:.1%}} of 2021–26 entries",f"same leading method with a 2019 boundary: {{stable}}"],"validation":"The leading method is re-evaluated after shifting the recent-era boundary by two years.","notebook":"exoplanet-archive/2026-07-31-exoplanet-discovery-method-timeline/notebook.ipynb","hero":"exoplanet-archive/2026-07-31-exoplanet-discovery-method-timeline/discovery_method_timeline.png","tags":["exoplanets","discovery history","selection effects"]}
Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "discovery_method_timeline.png")

    make_case("exoplanet-archive", "hot-jupiter-radius-inflation",
      "Hot-Jupiter radius inflation against stellar temperature",
      "Are close-in giant planets larger around hotter stars in this archive sample?", source_g,
      """Strongly irradiated giant planets often have radii larger than simple cooling models
      predict. Stellar effective temperature is only a proxy for incident flux because the
      orbital separation and stellar radius also matter. We therefore test a narrow empirical
      question: within giants orbiting in under ten days, does recorded radius increase with
      host temperature? A rank correlation avoids assuming a linear relationship.

      The test does not isolate inflation physics from planet mass, age, metallicity, or
      discovery bias. A mass-restricted repeat checks one obvious confounder. Published work on
      inflated hot Jupiters motivates the expectation; the archive table supplies the measured
      radii, periods, masses, and host temperatures.
      """,
      [f"""
raw = pd.read_csv("{source_g}").drop_duplicates("pl_name")
sample = raw.dropna(subset=["pl_orbper","pl_radj","st_teff"]).copy()
sample = sample[(sample.pl_orbper < 10) & sample.pl_radj.between(0.7,2.2) & sample.st_teff.between(3500,8000)]
print(f"Close-in giants with radius and Teff: {{len(sample):,}}")
""", """
rho, pvalue = stats.spearmanr(sample.st_teff, sample.pl_radj)
boot=[]
for _ in range(1000):
    take=sample.iloc[RNG.integers(0,len(sample),len(sample))]
    boot.append(stats.spearmanr(take.st_teff,take.pl_radj).statistic)
lo,hi=np.nanpercentile(boot,[16,84])
print(f"Spearman rho={{rho:.3f}}, p={{pvalue:.2g}}, bootstrap 68%={{lo:.3f}}–{{hi:.3f}}")
""", """
fig,ax=plt.subplots(figsize=(9,5.5)); sc=ax.scatter(sample.st_teff,sample.pl_radj,c=np.log10(sample.pl_orbper),s=18,alpha=.5,cmap="viridis")
ax.set(xlabel="Host effective temperature (K)",ylabel="Planet radius (Jupiter radii)",title="Close-in giant-planet radius and host temperature")
plt.colorbar(sc,ax=ax,label="log10 orbital period (days)"); fig.tight_layout(); fig.savefig("hot_jupiter_inflation.png",dpi=180); plt.show()
""", """
restricted=sample.dropna(subset=["pl_bmassj"]); restricted=restricted[restricted.pl_bmassj.between(.3,3)]
rho_mass=stats.spearmanr(restricted.st_teff,restricted.pl_radj).statistic
print(f"Mass-restricted N={{len(restricted)}}; rho={{rho_mass:.3f}}")
""", """
result={"id":"2026-07-31-hot-jupiter-radius-inflation","title":"Hot-Jupiter radius inflation","archive":"NASA Exoplanet Archive","date":"2026-07-31","question":"Are close-in giants larger around hotter stars?","sample_size":int(len(sample)),"results":[f"Spearman ρ = {{rho:.3f}}",f"bootstrap 68% interval {{lo:.3f}}–{{hi:.3f}}",f"mass-restricted ρ = {{rho_mass:.3f}} (N={{len(restricted)}})"],"validation":"The correlation is repeated for 0.3–3 Jupiter-mass planets.","notebook":"exoplanet-archive/2026-07-31-hot-jupiter-radius-inflation/notebook.ipynb","hero":"exoplanet-archive/2026-07-31-hot-jupiter-radius-inflation/hot_jupiter_inflation.png","tags":["hot Jupiters","radius inflation","rank correlation"]}
Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "hot_jupiter_inflation.png")

    make_case("exoplanet-archive", "eccentricity-discovery-bias",
      "Exoplanet eccentricity and discovery-method bias",
      "Do radial-velocity and transit discoveries have the same recorded eccentricity distribution?", source_g,
      """Eccentricity is difficult to measure near zero, and discovery techniques sample
      different orbital periods and planet masses. Comparing methods therefore diagnoses the
      archive's selection function as much as planet dynamics. We retain methods with enough
      measurements, compare medians and zero-valued fractions, and then repeat the calculation
      only where a quoted uncertainty is available.

      A significant difference cannot be read as a causal effect of discovery method. It is a
      warning that population claims need matched samples and hierarchical treatment of upper
      limits. The result complements the tidal-circularisation notebook by focusing on how the
      measurement channel changes the recorded population.
      """,
      [f"""
raw=pd.read_csv("{source_g}").drop_duplicates("pl_name")
sample=raw.dropna(subset=["pl_orbeccen","discoverymethod"]).copy(); sample=sample[sample.pl_orbeccen.between(0,1)]
keep=sample.discoverymethod.value_counts(); methods=keep[keep>=80].index
sample=sample[sample.discoverymethod.isin(methods)]
print(f"Planets with eccentricity in well-populated methods: {{len(sample):,}}")
""", """
summary=sample.groupby("discoverymethod").pl_orbeccen.agg(["count","median","mean"])
summary["zero_fraction"]=sample.assign(zero=sample.pl_orbeccen==0).groupby("discoverymethod").zero.mean()
groups=[g.pl_orbeccen.values for _,g in sample.groupby("discoverymethod")]
H,pvalue=stats.kruskal(*groups)
p_text="<1e-300" if pvalue == 0 else f"{{pvalue:.2g}}"
print(summary.round(3)); print(f"Kruskal–Wallis H={{H:.1f}}, p={{p_text}}")
""", """
order=summary.sort_values("median").index; data=[sample.loc[sample.discoverymethod==m,"pl_orbeccen"] for m in order]
fig,ax=plt.subplots(figsize=(10,5.5)); ax.boxplot(data,labels=order,showfliers=False); ax.set(ylabel="Recorded eccentricity",title="Eccentricity distributions differ across discovery channels"); ax.tick_params(axis="x",rotation=20); fig.tight_layout(); fig.savefig("eccentricity_by_method.png",dpi=180); plt.show()
""", """
precise=sample.dropna(subset=["pl_orbeccenerr1","pl_orbeccenerr2"]).copy(); precise["e_err"]=(precise.pl_orbeccenerr1.abs()+precise.pl_orbeccenerr2.abs())/2
precise=precise[precise.e_err<.1]; med_precise=precise.groupby("discoverymethod").pl_orbeccen.median()
print("Medians with quoted error <0.1:"); print(med_precise.round(3))
""", """
largest=summary["median"].idxmax(); smallest=summary["median"].idxmin()
result={"id":"2026-07-31-eccentricity-discovery-bias","title":"Eccentricity and discovery bias","archive":"NASA Exoplanet Archive","date":"2026-07-31","question":"Do discovery methods share an eccentricity distribution?","sample_size":int(len(sample)),"results":[f"Kruskal–Wallis p = {{p_text}}",f"highest median: {{largest}} ({{summary.loc[largest,'median']:.3f}})",f"lowest median: {{smallest}} ({{summary.loc[smallest,'median']:.3f}})"],"validation":"Method medians are recomputed using only eccentricities with quoted error below 0.1.","notebook":"exoplanet-archive/2026-07-31-eccentricity-discovery-bias/notebook.ipynb","hero":"exoplanet-archive/2026-07-31-eccentricity-discovery-bias/eccentricity_by_method.png","tags":["eccentricity","selection bias","discovery method"]}
Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "eccentricity_by_method.png")

    make_case("exoplanet-archive", "single-vs-multiplanet-systems",
      "Planet sizes in single- and multi-transiting systems",
      "Does the archive show different radius distributions for hosts with one versus multiple transiting planets?", source_t,
      """Compact multi-planet systems are central to tests of planetary architecture. The
      preserved transit sample lets us count planets per host and compare the observed radius
      distributions of one-planet and multi-planet hosts. “Single” means one archived transiting
      planet in this table, not proof that no additional planet exists.

      Detection completeness is especially important: additional small or long-period planets
      can be missed. We use a rank test and bootstrap the median contrast, then restrict to
      discoveries before 2023 so the result is not driven only by the newest catalogue entries.
      """,
      [f"""
raw=pd.read_csv("{source_t}").drop_duplicates("pl_name")
sample=raw.dropna(subset=["hostname","pl_rade","pl_orbper"]).copy(); sample=sample[sample.pl_rade.between(.5,20)&sample.pl_orbper.between(.3,300)]
host_n=sample.groupby("hostname").pl_name.transform("count"); sample["architecture"]=np.where(host_n>1,"multi-host","single-host")
print(sample.architecture.value_counts()); print(f"Unique hosts: {{sample.hostname.nunique():,}}")
""", """
a=sample.loc[sample.architecture=="single-host","pl_rade"]; b=sample.loc[sample.architecture=="multi-host","pl_rade"]
contrast=float(np.median(b)-np.median(a)); U,pvalue=stats.mannwhitneyu(a,b,alternative="two-sided")
boot=[]
for _ in range(1000): boot.append(np.median(RNG.choice(b,len(b)))-np.median(RNG.choice(a,len(a))))
lo,hi=np.percentile(boot,[2.5,97.5]); print(f"Median contrast multi-single={{contrast:.2f}} R_earth; 95% {{lo:.2f}} to {{hi:.2f}}")
""", """
fig,ax=plt.subplots(figsize=(9,5.5)); bins=np.logspace(np.log10(.5),np.log10(20),35)
ax.hist(a,bins=bins,density=True,histtype="step",lw=2,label=f"single host (N={{len(a)}})"); ax.hist(b,bins=bins,density=True,histtype="step",lw=2,label=f"multi host (N={{len(b)}})")
ax.set_xscale("log"); ax.set(xlabel="Planet radius (Earth radii)",ylabel="Density",title="Observed planet-size distributions by host multiplicity"); ax.legend(); fig.tight_layout(); fig.savefig("single_multi_radius.png",dpi=180); plt.show()
""", """
old=sample[sample.disc_year<=2022]; old_n=old.groupby("hostname").pl_name.transform("count"); old=old.assign(architecture=np.where(old_n>1,"multi-host","single-host"))
old_a=old.loc[old.architecture=="single-host","pl_rade"]; old_b=old.loc[old.architecture=="multi-host","pl_rade"]; old_contrast=float(np.median(old_b)-np.median(old_a))
print(f"Pre-2023 contrast={{old_contrast:.2f}} R_earth")
""", """
result={"id":"2026-07-31-single-vs-multiplanet-systems","title":"Single versus multi-transiting systems","archive":"NASA Exoplanet Archive","date":"2026-07-31","question":"Do archived planet radii differ with host multiplicity?","sample_size":int(len(sample)),"results":[f"median radius contrast {{contrast:.2f}} Earth radii",f"bootstrap 95% {{lo:.2f}} to {{hi:.2f}}",f"pre-2023 contrast {{old_contrast:.2f}} Earth radii"],"validation":"The contrast is repeated after excluding discoveries later than 2022.","notebook":"exoplanet-archive/2026-07-31-single-vs-multiplanet-systems/notebook.ipynb","hero":"exoplanet-archive/2026-07-31-single-vs-multiplanet-systems/single_multi_radius.png","tags":["planet architecture","multiplicity","transits"]}
Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "single_multi_radius.png")


def sdss_cases() -> None:
    source = "../2026-07-31-sdss-bpt-galaxy-classification/sdss_bpt_query.csv"
    common_load = f"""
raw=pd.read_csv("{source}")
lines=["h_alpha","h_beta","oiii_5007","nii_6584"]
sample=raw.copy()
for line in lines: sample=sample[(sample[f"{{line}}_flux"]>0)&(sample[f"{{line}}_flux_err"]>0)]
print(f"Positive four-line measurements: {{len(sample):,}} of {{len(raw):,}}")
"""
    make_case("sdss", "balmer-decrement-dust",
      "Balmer decrement as a dust indicator in SDSS galaxies",
      "What colour excess is implied by the observed H-alpha to H-beta ratio?", source,
      """Hydrogen recombination predicts an intrinsic H-alpha/H-beta ratio near 2.86 for
      standard nebular conditions. Dust removes more blue H-beta light, increasing the ratio.
      We convert the observed ratio to an approximate colour excess using a commonly adopted
      optical attenuation curve and report the median with a bootstrap interval.

      Stellar absorption beneath H-beta, aperture effects, flux calibration, and different
      nebular conditions can mimic part of the change. The estimate is therefore a diagnostic,
      not a full dust model. Raising the four-line signal-to-noise threshold tests whether noisy
      denominators dominate the result.
      """,
      [common_load, """
for line in lines: sample[f"snr_{line}"]=sample[f"{line}_flux"]/sample[f"{line}_flux_err"]
clean=sample[(sample[[f"snr_{x}" for x in lines]]>=5).all(axis=1)].copy(); clean["balmer"]=clean.h_alpha_flux/clean.h_beta_flux
clean=clean[clean.balmer.between(2,12)]; kHb,kHa=3.61,2.53; clean["ebv"]=2.5/(kHb-kHa)*np.log10(clean.balmer/2.86)
median=float(clean.ebv.median()); boot=[clean.ebv.sample(len(clean),replace=True,random_state=i).median() for i in range(500)]; lo,hi=np.percentile(boot,[16,84])
print(f"N={len(clean):,}; median E(B-V)={median:.3f}; 68% {lo:.3f}–{hi:.3f}")
""", """
fig,ax=plt.subplots(figsize=(9,5.3)); ax.hist(clean.ebv,bins=60,color=COLORS["blue"],alpha=.8); ax.axvline(median,color=COLORS["orange"],lw=2,label=f"median {median:.2f}"); ax.set(xlabel="Approximate nebular E(B−V) (mag)",ylabel="Galaxies",title="Dust indicator from the Balmer decrement"); ax.legend(); fig.tight_layout(); fig.savefig("balmer_decrement_dust.png",dpi=180); plt.show()
""", """
strict=sample[(sample[[f"snr_{x}" for x in lines]]>=8).all(axis=1)].copy(); strict["balmer"]=strict.h_alpha_flux/strict.h_beta_flux; strict=strict[strict.balmer.between(2,12)]; strict["ebv"]=2.5/(kHb-kHa)*np.log10(strict.balmer/2.86); strict_med=float(strict.ebv.median()); print(f"S/N≥8 median={strict_med:.3f} (N={len(strict):,})")
""", """
result={"id":"2026-07-31-balmer-decrement-dust","title":"SDSS Balmer-decrement dust indicator","archive":"SDSS","date":"2026-07-31","question":"What colour excess is implied by Hα/Hβ?","sample_size":int(len(clean)),"results":[f"median E(B−V) {{median:.3f}} mag",f"bootstrap 68% {{lo:.3f}}–{{hi:.3f}} mag",f"S/N≥8 median {{strict_med:.3f}} mag"],"validation":"The median is repeated with every emission line required at S/N≥8.","notebook":"sdss/2026-07-31-balmer-decrement-dust/notebook.ipynb","hero":"sdss/2026-07-31-balmer-decrement-dust/balmer_decrement_dust.png","tags":["Balmer decrement","dust","emission lines"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "balmer_decrement_dust.png")

    make_case("sdss", "n2-metallicity-proxy",
      "Gas-phase metallicity from the SDSS N2 proxy",
      "What oxygen-abundance distribution is implied for the star-forming BPT branch?", source,
      """The ratio [N II]6584/H-alpha changes with gas composition and ionisation state.
      For galaxies below the empirical star-forming BPT boundary, the N2 calibration gives a
      convenient approximate oxygen abundance. We enforce four-line signal-to-noise, limit the
      ratio to the calibration range, bootstrap the median, and check a stricter threshold.

      N2 saturates near high metallicity and depends on nitrogen-to-oxygen abundance and
      ionisation parameter. The number is a strong-line calibration result, not a direct count
      of oxygen atoms. Mixing calibrations would introduce systematic offsets larger than the
      quoted resampling uncertainty.
      """,
      [common_load, """
for line in lines: sample[f"snr_{line}"]=sample[f"{line}_flux"]/sample[f"{line}_flux_err"]
clean=sample[(sample[[f"snr_{x}" for x in lines]]>=5).all(axis=1)].copy(); clean["n2"]=np.log10(clean.nii_6584_flux/clean.h_alpha_flux); clean["o3"]=np.log10(clean.oiii_5007_flux/clean.h_beta_flux)
boundary=.61/(clean.n2-.05)+1.3; sf=clean[(clean.o3<boundary)&clean.n2.between(-2.5,-.3)].copy(); sf["oxygen_abundance"]=8.90+.57*sf.n2
median=float(sf.oxygen_abundance.median()); boot=[sf.oxygen_abundance.sample(len(sf),replace=True,random_state=i).median() for i in range(500)]; lo,hi=np.percentile(boot,[16,84]); print(f"Star-forming N={len(sf):,}; median 12+log(O/H)={median:.3f}")
""", """
fig,ax=plt.subplots(figsize=(9,5.3)); ax.hist(sf.oxygen_abundance,bins=55,color=COLORS["cyan"],alpha=.85); ax.axvline(median,color=COLORS["navy"],lw=2); ax.set(xlabel="12 + log(O/H), N2 calibration",ylabel="Galaxies",title="Approximate oxygen abundance on the star-forming branch"); fig.tight_layout(); fig.savefig("n2_metallicity_distribution.png",dpi=180); plt.show()
""", """
strict=sf[(sf[[f"snr_{x}" for x in lines]]>=8).all(axis=1)]; strict_med=float(strict.oxygen_abundance.median()); delta=strict_med-median; print(f"S/N≥8 median={strict_med:.3f}; shift={delta:+.3f} dex")
""", """
result={"id":"2026-07-31-n2-metallicity-proxy","title":"SDSS N2 metallicity proxy","archive":"SDSS","date":"2026-07-31","question":"What oxygen abundance does N2 imply on the star-forming branch?","sample_size":int(len(sf)),"results":[f"median 12+log(O/H) = {{median:.3f}}",f"bootstrap 68% {{lo:.3f}}–{{hi:.3f}}",f"S/N≥8 shift {{delta:+.3f}} dex"],"validation":"The abundance median is repeated at S/N≥8 for all four lines.","notebook":"sdss/2026-07-31-n2-metallicity-proxy/notebook.ipynb","hero":"sdss/2026-07-31-n2-metallicity-proxy/n2_metallicity_distribution.png","tags":["metallicity","N2","star-forming galaxies"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "n2_metallicity_distribution.png")

    make_case("sdss", "excitation-redshift-selection",
      "Emission-line excitation against redshift in SDSS",
      "Does the observed [O III]/H-beta ratio change across this low-redshift selected sample?", source,
      """[O III]/H-beta responds to ionisation state, metallicity, and hard radiation fields.
      We test its rank relation with redshift after requiring reliable positive line fluxes. Any
      trend is descriptive: a fixed fibre samples a different physical fraction of a galaxy as
      redshift changes, while a flux-limited survey changes the luminosity mix.

      Median ratios in redshift bins make the effect visible without assuming a straight line.
      The stress test narrows the redshift range to ask whether edge populations dominate. The
      analysis should be interpreted as a selection-function lesson, not galaxy evolution over
      this modest lookback-time interval.
      """,
      [common_load, """
sample["snr_hb"]=sample.h_beta_flux/sample.h_beta_flux_err; sample["snr_o3"]=sample.oiii_5007_flux/sample.oiii_5007_flux_err
clean=sample[(sample.snr_hb>=5)&(sample.snr_o3>=5)&sample.z.between(.01,.3)].copy(); clean["log_o3hb"]=np.log10(clean.oiii_5007_flux/clean.h_beta_flux)
rho,pvalue=stats.spearmanr(clean.z,clean.log_o3hb); print(f"N={len(clean):,}; rho={rho:.3f}; p={pvalue:.2g}")
""", """
clean["zbin"]=pd.qcut(clean.z,8,duplicates="drop"); trend=clean.groupby("zbin",observed=True).agg(z=("z","median"),ratio=("log_o3hb","median"),n=("z","size"))
fig,ax=plt.subplots(figsize=(9,5.3)); ax.scatter(clean.z,clean.log_o3hb,s=4,alpha=.08,color=COLORS["navy"]); ax.plot(trend.z,trend.ratio,"o-",color=COLORS["orange"],lw=2,label="bin medians"); ax.set(xlabel="Redshift",ylabel="log10([O III]/Hβ)",title="Observed excitation proxy and redshift"); ax.legend(); fig.tight_layout(); fig.savefig("excitation_redshift.png",dpi=180); plt.show()
""", """
central=clean[clean.z.between(.03,.2)]; rho_c,p_c=stats.spearmanr(central.z,central.log_o3hb); print(f"0.03<z<0.20: N={len(central):,}, rho={rho_c:.3f}")
""", """
result={"id":"2026-07-31-excitation-redshift-selection","title":"SDSS excitation versus redshift","archive":"SDSS","date":"2026-07-31","question":"Does [O III]/Hβ vary with redshift in the selected sample?","sample_size":int(len(clean)),"results":[f"Spearman ρ = {{rho:.3f}}",f"p = {{pvalue:.2g}}",f"restricted-range ρ = {{rho_c:.3f}}"],"validation":"The rank test is repeated over 0.03<z<0.20.","notebook":"sdss/2026-07-31-excitation-redshift-selection/notebook.ipynb","hero":"sdss/2026-07-31-excitation-redshift-selection/excitation_redshift.png","tags":["excitation","redshift","selection effects"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "excitation_redshift.png")

    make_case("sdss", "bpt-snr-sensitivity",
      "How BPT class fractions depend on line signal-to-noise",
      "How much do star-forming, composite, and AGN fractions move when the line-quality threshold changes?", source,
      """A BPT diagram is only as reliable as its weakest line. Requiring higher
      signal-to-noise improves ratio precision but preferentially removes weak-line galaxies,
      so class fractions can change even if the boundaries stay fixed. We calculate the same
      Kauffmann and Kewley divisions at thresholds of 3, 5, 8, and 10.

      The spread across thresholds is treated as a practical selection systematic. It is not a
      formal uncertainty on the cosmic abundance of active galaxies because this table was
      already selected for usable lines and does not include the full SDSS targeting function.
      """,
      [common_load, """
def classify(d,threshold):
    x=d.copy()
    for line in lines: x=x[x[f"{line}_flux"]/x[f"{line}_flux_err"]>=threshold]
    x=x.copy(); x["n2"]=np.log10(x.nii_6584_flux/x.h_alpha_flux); x["o3"]=np.log10(x.oiii_5007_flux/x.h_beta_flux); x=x[x.n2<.4]
    kauff=.61/(x.n2-.05)+1.3; kew=.61/(x.n2-.47)+1.19
    x["class"]=np.select([x.o3<kauff,x.o3<kew],["Star forming","Composite"],default="AGN")
    return x
rows=[]
for t in [3,5,8,10]:
    x=classify(sample,t); f=x["class"].value_counts(normalize=True); rows.append({"snr":t,"n":len(x),**f.to_dict()})
summary=pd.DataFrame(rows).fillna(0); print(summary.round(3))
""", """
fig,ax=plt.subplots(figsize=(9,5.3)); bottom=np.zeros(len(summary));
for label,color in zip(["Star forming","Composite","AGN"],[COLORS["blue"],COLORS["gold"],COLORS["rose"]]):
    ax.bar(summary.snr,summary[label],bottom=bottom,label=label,color=color,width=1.3); bottom+=summary[label].to_numpy()
ax.set(xlabel="Minimum S/N in all four lines",ylabel="Class fraction",title="BPT fractions shift with the quality threshold"); ax.legend(); fig.tight_layout(); fig.savefig("bpt_snr_sensitivity.png",dpi=180); plt.show()
""", """
agn3=float(summary.loc[summary.snr==3,"AGN"].iloc[0]); agn10=float(summary.loc[summary.snr==10,"AGN"].iloc[0]); spread=agn10-agn3; retained=int(summary.loc[summary.snr==10,"n"].iloc[0]); print(f"AGN fraction shift S/N 3→10: {spread:+.1%}; retained N={retained:,}")
""", """
result={"id":"2026-07-31-bpt-snr-sensitivity","title":"BPT sensitivity to line quality","archive":"SDSS","date":"2026-07-31","question":"How do class fractions move with emission-line S/N?","sample_size":int(summary.loc[summary.snr==3,"n"].iloc[0]),"results":[f"AGN-fraction shift S/N 3→10: {{spread:+.1%}}",f"S/N≥10 retains {{retained:,}} galaxies",f"four thresholds tested: 3, 5, 8, 10"],"validation":"Class fractions are recomputed at four complete four-line thresholds.","notebook":"sdss/2026-07-31-bpt-snr-sensitivity/notebook.ipynb","hero":"sdss/2026-07-31-bpt-snr-sensitivity/bpt_snr_sensitivity.png","tags":["BPT","quality control","selection effects"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "bpt_snr_sensitivity.png")


def gaia_cases() -> None:
    source = "../2026-07-31-gaia-pleiades-membership-distance/pleiades_members.csv"
    common = f"""
members=pd.read_csv("{source}"); members=members[members.member.astype(bool)].copy()
members=members.dropna(subset=["parallax","parallax_error","pmra","pmdec","phot_g_mean_mag","bp_rp","ruwe"])
members["abs_g"]=members.phot_g_mean_mag+5*np.log10(members.parallax)-10
print(f"Preserved astrometric members: {{len(members)}}")
"""
    make_case("gaia", "pleiades-cmd-ruwe-binaries",
      "Pleiades colour–magnitude outliers and Gaia RUWE",
      "Are stars above the fitted single-star sequence more likely to have elevated RUWE?", source,
      """Unresolved binaries can appear brighter than a single star of the same colour and can
      also disturb a single-source astrometric fit. Gaia's renormalised unit weight error (RUWE)
      is a fit-quality diagnostic, not a binary flag by itself. We fit a robust polynomial to
      the cluster colour–magnitude sequence and compare vertical residuals with RUWE.

      Crowding, variability, calibration, and the sequence fit also create outliers. The test
      therefore identifies candidates for follow-up, not confirmed companions. Changing the
      RUWE threshold checks how dependent the fraction is on a conventional cut.
      """,
      [common, """
fit=members[members.bp_rp.between(.2,3.2)&members.abs_g.between(-2,13)].copy(); coef=np.polyfit(fit.bp_rp,fit.abs_g,4); fit["sequence"]=np.polyval(coef,fit.bp_rp); fit["delta_g"]=fit.abs_g-fit.sequence
bright=fit.delta_g<-.45; elevated=fit.ruwe>1.2; table=pd.crosstab(bright,elevated); odds,pvalue=stats.fisher_exact(table); print(table); print(f"odds ratio={odds:.2f}, p={pvalue:.3g}")
""", """
fig,ax=plt.subplots(figsize=(8,6)); sc=ax.scatter(fit.bp_rp,fit.abs_g,c=fit.ruwe,s=17,cmap="viridis",vmin=.8,vmax=1.4); x=np.linspace(.2,3.2,300); ax.plot(x,np.polyval(coef,x),color=COLORS["orange"],lw=2,label="sequence fit"); ax.invert_yaxis(); ax.set(xlabel="BP−RP (mag)",ylabel="Absolute G (mag)",title="Pleiades sequence coloured by astrometric fit quality"); ax.legend(); plt.colorbar(sc,ax=ax,label="RUWE"); fig.tight_layout(); fig.savefig("pleiades_cmd_ruwe.png",dpi=180); plt.show()
""", """
elevated_alt=fit.ruwe>1.1; table_alt=pd.crosstab(bright,elevated_alt); odds_alt,p_alt=stats.fisher_exact(table_alt); print(f"RUWE>1.1 odds ratio={odds_alt:.2f}, p={p_alt:.3g}")
""", """
result={"id":"2026-07-31-pleiades-cmd-ruwe-binaries","title":"Pleiades CMD outliers and RUWE","archive":"Gaia DR3","date":"2026-07-31","question":"Do over-luminous candidates have elevated RUWE more often?","sample_size":int(len(fit)),"results":[f"RUWE>1.2 odds ratio {{odds:.2f}}",f"Fisher-test p = {{pvalue:.3g}}",f"RUWE>1.1 odds ratio {{odds_alt:.2f}}"],"validation":"The contingency test is repeated at RUWE thresholds 1.2 and 1.1.","notebook":"gaia/2026-07-31-pleiades-cmd-ruwe-binaries/notebook.ipynb","hero":"gaia/2026-07-31-pleiades-cmd-ruwe-binaries/pleiades_cmd_ruwe.png","tags":["Pleiades","RUWE","binary candidates"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "pleiades_cmd_ruwe.png")

    make_case("gaia", "pleiades-mass-segregation-proxy",
      "A projected mass-segregation proxy in the Pleiades",
      "Are brighter cluster members more centrally concentrated on the sky?", source,
      """In a coeval cluster, brighter main-sequence stars are usually more massive, so their
      projected concentration is a simple mass-segregation proxy. We calculate angular distance
      from a robust cluster centre and compare bright and faint halves. This is not a dynamical
      model: luminosity is altered by binaries and evolution, and the query footprint can cut
      off the outer population.

      A permutation test asks whether the median-radius contrast is larger than expected after
      shuffling brightness labels. Moving the brightness split by one magnitude tests whether a
      single median boundary creates the result.
      """,
      [common, """
ra0,dec0=members.ra.median(),members.dec.median(); dra=(members.ra-ra0)*np.cos(np.deg2rad(dec0)); ddec=members.dec-dec0; members["radius_deg"]=np.hypot(dra,ddec)
split=members.phot_g_mean_mag.median(); bright=members[members.phot_g_mean_mag<=split].radius_deg; faint=members[members.phot_g_mean_mag>split].radius_deg; contrast=float(np.median(faint)-np.median(bright)); print(f"median radius faint-bright={contrast:.3f} deg")
""", """
labels=np.r_[np.zeros(len(bright)),np.ones(len(faint))]; radii=np.r_[bright,faint]; perm=[]
for _ in range(2000):
    RNG.shuffle(labels); perm.append(np.median(radii[labels==1])-np.median(radii[labels==0]))
pvalue=(np.sum(np.asarray(perm)>=contrast)+1)/(len(perm)+1); print(f"one-sided permutation p={pvalue:.4f}")
fig,ax=plt.subplots(figsize=(8.5,5.3)); ax.hist(bright,bins=30,density=True,histtype="step",lw=2,label="brighter half"); ax.hist(faint,bins=30,density=True,histtype="step",lw=2,label="fainter half"); ax.set(xlabel="Angular radius from robust centre (deg)",ylabel="Density",title="Projected concentration by apparent brightness"); ax.legend(); fig.tight_layout(); fig.savefig("pleiades_mass_segregation.png",dpi=180); plt.show()
""", """
cut=15; b2=members[members.phot_g_mean_mag<=cut].radius_deg; f2=members[members.phot_g_mean_mag>cut].radius_deg; contrast2=float(np.median(f2)-np.median(b2)); print(f"Fixed G=15 split contrast={contrast2:.3f} deg")
""", """
result={"id":"2026-07-31-pleiades-mass-segregation-proxy","title":"Pleiades mass-segregation proxy","archive":"Gaia DR3","date":"2026-07-31","question":"Are brighter members more centrally concentrated?","sample_size":int(len(members)),"results":[f"faint-minus-bright median radius {{contrast:.3f}}°",f"permutation p = {{pvalue:.4f}}",f"fixed G=15 contrast {{contrast2:.3f}}°"],"validation":"The brightness division is changed from the sample median to G=15.","notebook":"gaia/2026-07-31-pleiades-mass-segregation-proxy/notebook.ipynb","hero":"gaia/2026-07-31-pleiades-mass-segregation-proxy/pleiades_mass_segregation.png","tags":["Pleiades","mass segregation","spatial distribution"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "pleiades_mass_segregation.png")

    make_case("gaia", "pleiades-proper-motion-dispersion",
      "Pleiades proper-motion dispersion after measurement errors",
      "How much proper-motion scatter remains after subtracting the reported Gaia uncertainties?", source,
      """The observed width of a cluster's proper-motion clump combines internal motion,
      binaries, contamination, perspective effects, and measurement error. We estimate the
      intrinsic component by subtracting the mean squared formal error from the robust observed
      variance in each coordinate, then convert milliarcseconds per year to kilometres per
      second using the mean parallax.

      This scalar deconvolution ignores covariance and spatial perspective, so it is a diagnostic
      rather than a final velocity-dispersion measurement. Restricting to brighter stars checks
      whether faint-source uncertainty dominates.
      """,
      [common, """
def robust_sigma(x): return 1.4826*np.median(np.abs(x-np.median(x)))
sx,sy=robust_sigma(members.pmra),robust_sigma(members.pmdec); ex=np.sqrt(np.mean(members.pmra_error**2)); ey=np.sqrt(np.mean(members.pmdec_error**2)); ix=np.sqrt(max(0,sx*sx-ex*ex)); iy=np.sqrt(max(0,sy*sy-ey*ey)); par=members.parallax.mean(); vx=4.74047*ix/par; vy=4.74047*iy/par
print(f"observed σ=({sx:.3f},{sy:.3f}) mas/yr; deconvolved=({ix:.3f},{iy:.3f}); velocity=({vx:.3f},{vy:.3f}) km/s")
""", """
fig,ax=plt.subplots(figsize=(7,6)); ax.scatter(members.pmra,members.pmdec,s=10,alpha=.35,color=COLORS["blue"]); ax.axvline(members.pmra.median(),color="k",lw=1); ax.axhline(members.pmdec.median(),color="k",lw=1); ax.set(xlabel="pmRA (mas yr⁻¹)",ylabel="pmDec (mas yr⁻¹)",title="Pleiades proper-motion clump"); fig.tight_layout(); fig.savefig("pleiades_pm_dispersion.png",dpi=180); plt.show()
""", """
bright=members[members.phot_g_mean_mag<15]; sx_b,sy_b=robust_sigma(bright.pmra),robust_sigma(bright.pmdec); ex_b=np.sqrt(np.mean(bright.pmra_error**2)); ey_b=np.sqrt(np.mean(bright.pmdec_error**2)); ix_b=np.sqrt(max(0,sx_b*sx_b-ex_b*ex_b)); iy_b=np.sqrt(max(0,sy_b*sy_b-ey_b*ey_b)); print(f"G<15 deconvolved σ=({ix_b:.3f},{iy_b:.3f}) mas/yr, N={len(bright)}")
""", """
result={"id":"2026-07-31-pleiades-proper-motion-dispersion","title":"Pleiades proper-motion dispersion","archive":"Gaia DR3","date":"2026-07-31","question":"What scatter remains after formal-error subtraction?","sample_size":int(len(members)),"results":[f"deconvolved σRA {{ix:.3f}} mas/yr",f"deconvolved σDec {{iy:.3f}} mas/yr",f"velocity equivalents {{vx:.3f}}, {{vy:.3f}} km/s"],"validation":"The calculation is repeated for G<15 members.","notebook":"gaia/2026-07-31-pleiades-proper-motion-dispersion/notebook.ipynb","hero":"gaia/2026-07-31-pleiades-proper-motion-dispersion/pleiades_pm_dispersion.png","tags":["Pleiades","proper motion","kinematics"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "pleiades_pm_dispersion.png")

    make_case("gaia", "pleiades-line-of-sight-depth",
      "Can Gaia resolve the Pleiades line-of-sight depth?",
      "Is the observed parallax width larger than the reported measurement errors?", source,
      """A cluster has finite physical depth, so perfect parallaxes would not all be identical.
      We compare the robust observed parallax width with the root-mean-square formal uncertainty
      and subtract variances to estimate a residual width. A first-order derivative converts
      parallax scatter into parsecs around the mean distance.

      Spatially correlated Gaia systematics and residual contamination are not included in the
      formal errors and can mimic depth. We therefore repeat the calculation for bright stars
      and describe the result as an upper-limit-style diagnostic, not a geometric map of the
      cluster.
      """,
      [common, """
def depth_estimate(d):
    p=d.parallax.to_numpy(); obs=1.4826*np.median(np.abs(p-np.median(p))); err=np.sqrt(np.mean(d.parallax_error**2)); intrinsic=np.sqrt(max(0,obs**2-err**2)); mean=np.mean(p); depth=1000*intrinsic/mean**2; return obs,err,intrinsic,depth
obs,err,intrinsic,depth=depth_estimate(members); print(f"robust observed σ={obs:.4f} mas; RMS error={err:.4f}; residual={intrinsic:.4f} mas; depth proxy={depth:.2f} pc")
""", """
boot=[]
for _ in range(1000): boot.append(depth_estimate(members.iloc[RNG.integers(0,len(members),len(members))])[-1])
lo,hi=np.percentile(boot,[16,84]); fig,ax=plt.subplots(figsize=(8.5,5.3)); ax.hist(members.parallax,bins=45,color=COLORS["cyan"],alpha=.8); ax.set(xlabel="Parallax (mas)",ylabel="Members",title="Pleiades member parallax distribution"); fig.tight_layout(); fig.savefig("pleiades_depth.png",dpi=180); plt.show(); print(f"bootstrap 68% depth proxy={lo:.2f}–{hi:.2f} pc")
""", """
bright=members[members.phot_g_mean_mag<15]; _,_,intr_b,depth_b=depth_estimate(bright); print(f"G<15 residual={intr_b:.4f} mas; depth proxy={depth_b:.2f} pc")
""", """
result={"id":"2026-07-31-pleiades-line-of-sight-depth","title":"Pleiades line-of-sight depth proxy","archive":"Gaia DR3","date":"2026-07-31","question":"Is the parallax width larger than formal errors?","sample_size":int(len(members)),"results":[f"residual parallax width {{intrinsic:.4f}} mas",f"depth proxy {{depth:.2f}} pc",f"bootstrap 68% {{lo:.2f}}–{{hi:.2f}} pc"],"validation":"The variance subtraction is repeated for G<15 stars.","notebook":"gaia/2026-07-31-pleiades-line-of-sight-depth/notebook.ipynb","hero":"gaia/2026-07-31-pleiades-line-of-sight-depth/pleiades_depth.png","tags":["Pleiades","parallax","cluster depth"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "pleiades_depth.png")


def mast_cases() -> None:
    source = "../2026-07-31-hst-stis-hd93521-line-inventory/spectrum_subset.csv"
    make_case("mast", "hst-stis-continuum-slope",
      "Optical continuum slope of HD 93521 with HST/STIS",
      "What power-law slope describes the calibrated optical continuum after masking strong lines?", source,
      """A hot star's optical spectrum lies toward the Rayleigh–Jeans side of its spectral
      energy distribution, but extinction and instrument calibration modify the observed slope.
      We fit log flux against log wavelength after masking known hydrogen and helium features.
      The fitted exponent is an empirical continuum descriptor, not a temperature measurement.

      STIS flux calibration is well characterised but finite; slit placement, extinction, line
      blanketing, and the limited 5300–10000 Å range remain important. Varying the line-mask
      width tests whether broad absorption features control the answer.
      """,
      [f"""
spec=pd.read_csv("{source}").dropna(); spec=spec[(spec.flux>0)&(spec.error>0)].copy(); lines=np.array([5411.52,5875.62,6562.80,6678.15,7065.19]); print(f"Calibrated samples: {{len(spec)}} over {{spec.wavelength_A.min():.0f}}–{{spec.wavelength_A.max():.0f}} Å")
""", """
def fit_slope(width):
    keep=np.ones(len(spec),dtype=bool)
    for line in lines: keep &= np.abs(spec.wavelength_A-line)>width
    x=np.log(spec.loc[keep,"wavelength_A"]); y=np.log(spec.loc[keep,"flux"]); w=1/(spec.loc[keep,"error"]/spec.loc[keep,"flux"])**2; coef=np.polyfit(x,y,1,w=np.sqrt(w)); return coef,keep
coef,keep=fit_slope(35); slope=float(coef[0]); boot=[]
idx=np.flatnonzero(keep)
for _ in range(1000):
    take=RNG.choice(idx,len(idx)); boot.append(np.polyfit(np.log(spec.wavelength_A.iloc[take]),np.log(spec.flux.iloc[take]),1)[0])
lo,hi=np.percentile(boot,[16,84]); print(f"F_lambda slope={slope:.3f}; bootstrap 68% {lo:.3f}–{hi:.3f}")
""", """
model=np.exp(np.polyval(coef,np.log(spec.wavelength_A))); fig,ax=plt.subplots(figsize=(10,5.3)); ax.loglog(spec.wavelength_A,spec.flux,color=COLORS["navy"],lw=1,label="STIS"); ax.loglog(spec.wavelength_A,model,color=COLORS["orange"],lw=2,label=f"power law α={slope:.2f}"); ax.set(xlabel="Wavelength (Å)",ylabel="Flux density",title="HD 93521 optical continuum descriptor"); ax.legend(); fig.tight_layout(); fig.savefig("hd93521_continuum_slope.png",dpi=180); plt.show()
""", """
s20=float(fit_slope(20)[0][0]); s50=float(fit_slope(50)[0][0]); print(f"mask widths 20/35/50 Å: {s20:.3f}, {slope:.3f}, {s50:.3f}")
""", """
result={"id":"2026-07-31-hst-stis-continuum-slope","title":"HST/STIS continuum slope of HD 93521","archive":"MAST · HST","date":"2026-07-31","question":"What power law describes the optical continuum?","sample_size":int(keep.sum()),"results":[f"Fλ exponent {{slope:.3f}}",f"bootstrap 68% {{lo:.3f}}–{{hi:.3f}}",f"20–50 Å masks give {{s20:.3f}} to {{s50:.3f}}"],"validation":"Strong-line mask widths of 20, 35, and 50 Å are compared.","notebook":"mast/2026-07-31-hst-stis-continuum-slope/notebook.ipynb","hero":"mast/2026-07-31-hst-stis-continuum-slope/hd93521_continuum_slope.png","tags":["HST","STIS","continuum"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "hd93521_continuum_slope.png")

    make_case("mast", "hst-halpha-equivalent-width-systematics",
      "How continuum choices change H-alpha equivalent width",
      "How stable is the measured H-alpha equivalent width to integration and continuum choices?", source,
      """Equivalent width is attractive because it measures a line relative to its local
      continuum, but the result depends on continuum windows and integration limits. We measure
      H-alpha in the calibrated STIS spectrum across a grid of line half-widths and polynomial
      continuum orders. The spread is reported as a practical method systematic.

      The low-resolution stellar feature may blend with neighbouring structure. The grid does
      not cover all possible models and is not a substitute for forward modelling the STIS line
      spread function. It does show whether a quoted value is robust to reasonable local choices.
      """,
      [f"""
spec=pd.read_csv("{source}").dropna(); wave=spec.wavelength_A.to_numpy(); flux=spec.flux.to_numpy(); error=spec.error.to_numpy(); centre=6562.8; print(f"Spectrum samples: {{len(spec)}}")
""", """
def measure_ew(half_width,order):
    side=((wave>centre-90)&(wave<centre-half_width-8))|((wave>centre+half_width+8)&(wave<centre+90)); line=np.abs(wave-centre)<=half_width
    coef=np.polyfit(wave[side]-centre,flux[side],order,w=1/error[side]); cont=np.polyval(coef,wave[line]-centre); return float(np.trapezoid(1-flux[line]/cont,wave[line]))
rows=[]
for width in [25,35,45,55,65]:
    for order in [1,2]: rows.append({"half_width_A":width,"order":order,"ew_A":measure_ew(width,order)})
grid=pd.DataFrame(rows); median=float(grid.ew_A.median()); spread=float(grid.ew_A.max()-grid.ew_A.min()); print(grid.round(3)); print(f"median EW={median:.3f} Å; full method spread={spread:.3f} Å")
""", """
fig,ax=plt.subplots(figsize=(8.5,5.3));
for order,g in grid.groupby("order"): ax.plot(g.half_width_A,g.ew_A,"o-",lw=2,label=f"continuum order {order}")
ax.set(xlabel="Line integration half-width (Å)",ylabel="Hα equivalent width (Å)",title="Method dependence of the Hα measurement"); ax.legend(); fig.tight_layout(); fig.savefig("halpha_ew_systematics.png",dpi=180); plt.show()
""", """
base=measure_ew(45,1); fractional=spread/abs(base); print(f"Reference 45 Å linear-continuum EW={base:.3f} Å; grid spread/reference={fractional:.1%}")
""", """
result={"id":"2026-07-31-hst-halpha-equivalent-width-systematics","title":"HST Hα equivalent-width systematics","archive":"MAST · HST","date":"2026-07-31","question":"How stable is Hα equivalent width to continuum choices?","sample_size":int(len(spec)),"results":[f"grid median EW {{median:.3f}} Å",f"method spread {{spread:.3f}} Å",f"spread/reference {{fractional:.1%}}"],"validation":"Five integration widths and two continuum orders are compared.","notebook":"mast/2026-07-31-hst-halpha-equivalent-width-systematics/notebook.ipynb","hero":"mast/2026-07-31-hst-halpha-equivalent-width-systematics/halpha_ew_systematics.png","tags":["HST","H-alpha","equivalent width","systematics"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "halpha_ew_systematics.png")

    image_source = "../2026-07-30-hst-cutout-m87/m87.jpg"
    make_case("mast", "hst-m87-image-morphology",
      "M87 morphology in an HST preview image",
      "What centroid, ellipticity, and half-light radius are measured from the preserved HST preview?", image_source,
      """This notebook treats the real HST-derived M87 preview as a two-dimensional image and
      measures reproducible morphology proxies. Background-subtracted intensity moments give a
      centroid and axis ratio; the cumulative radial profile gives a half-light radius in pixels.
      Because the input is a display JPEG rather than calibrated FITS, no physical surface
      brightness, colour, or absolute angular size is claimed.

      Compression, display stretch, crop, point sources, and the unknown preview transformation
      all affect the moments. Repeating the measurement at several background percentiles shows
      how much the derived morphology depends on thresholding. A later notebook should retrieve
      calibrated HST exposures and use the WCS and point-spread function.
      """,
      [f"""
from PIL import Image
img=np.asarray(Image.open("{image_source}").convert("L"),dtype=float); print(f"Preview shape: {{img.shape}}, dynamic range {{img.min():.0f}}–{{img.max():.0f}}")
""", """
def morphology(percentile):
    background=np.percentile(img,percentile); weight=np.clip(img-background,0,None); y,x=np.indices(img.shape); total=weight.sum(); xc=(x*weight).sum()/total; yc=(y*weight).sum()/total; dx=x-xc; dy=y-yc; Ixx=(weight*dx*dx).sum()/total; Iyy=(weight*dy*dy).sum()/total; Ixy=(weight*dx*dy).sum()/total; eig=np.linalg.eigvalsh([[Ixx,Ixy],[Ixy,Iyy]]); axis=np.sqrt(eig[0]/eig[1]); r=np.hypot(dx,dy).ravel(); w=weight.ravel(); order=np.argsort(r); cum=np.cumsum(w[order]); rhalf=r[order][np.searchsorted(cum,.5*cum[-1])]; return xc,yc,axis,rhalf,background
xc,yc,axis,rhalf,bg=morphology(20); print(f"centroid=({xc:.1f},{yc:.1f}) px; axis ratio={axis:.3f}; half-light radius={rhalf:.1f} px")
""", """
y,x=np.indices(img.shape); r=np.hypot(x-xc,y-yc); bins=np.linspace(0,np.percentile(r,95),80); profile=[]
for a,b in zip(bins[:-1],bins[1:]): profile.append(np.median(img[(r>=a)&(r<b)]))
fig,axes=plt.subplots(1,2,figsize=(12,5)); axes[0].imshow(img,cmap="gray",origin="lower"); axes[0].plot(xc,yc,"+",color="cyan",ms=14,mew=2); axes[0].set_title("Preserved HST preview and intensity centroid"); axes[1].plot((bins[:-1]+bins[1:])/2,profile,color=COLORS["navy"]); axes[1].axvline(rhalf,color=COLORS["orange"],label=f"half-light radius {rhalf:.0f} px"); axes[1].set(xlabel="Circular radius (pixels)",ylabel="Median display value",title="Radial display-intensity profile"); axes[1].legend(); fig.tight_layout(); fig.savefig("m87_preview_morphology.png",dpi=180); plt.show()
""", """
tests={p:morphology(p) for p in [10,20,30,40]}; axes_test=[v[2] for v in tests.values()]; radii_test=[v[3] for v in tests.values()]; print("Threshold tests:", {p:(round(v[2],3),round(v[3],1)) for p,v in tests.items()})
""", """
result={"id":"2026-07-31-hst-m87-image-morphology","title":"M87 morphology in an HST preview","archive":"MAST · HST","date":"2026-07-31","question":"What morphology proxies are measured from the preserved preview?","sample_size":int(img.size),"results":[f"axis ratio {{axis:.3f}}",f"half-light radius {{rhalf:.1f}} display pixels",f"threshold-test radius range {{min(radii_test):.1f}}–{{max(radii_test):.1f}} px"],"validation":"Moments are recomputed at four background percentiles.","notebook":"mast/2026-07-31-hst-m87-image-morphology/notebook.ipynb","hero":"mast/2026-07-31-hst-m87-image-morphology/m87_preview_morphology.png","tags":["HST","M87","image morphology","display image"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""], "m87_preview_morphology.png")


def main() -> None:
    exoplanet_cases()
    sdss_cases()
    gaia_cases()
    mast_cases()
    print("Generated 15 notebooks for the 50-notebook milestone")


if __name__ == "__main__":
    main()
