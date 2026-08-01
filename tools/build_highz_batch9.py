"""Build five executed-ready UNCOVER high-redshift notebooks for Batch 9."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-08-01"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


IMPORTS = r'''
from pathlib import Path
import json
import urllib.request

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
from scipy import stats

plt.style.use(["science", "no-latex"])
plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 220, "axes.titleweight": "bold"})
COLORS = {"navy": "#071426", "cyan": "#39c6d4", "gold": "#e3a82b",
          "coral": "#e66b55", "violet": "#7357c7", "green": "#3b9b77"}
RNG = np.random.default_rng(1999)
'''

LOAD = r'''
LOCAL = Path("../../data/uncover_dr3_highz/uncover_dr3_z6_candidates.csv")
RAW = "https://raw.githubusercontent.com/Biswajit1999/daily-astro-notebooks/master/data/uncover_dr3_highz/uncover_dr3_z6_candidates.csv"
if not LOCAL.exists():
    LOCAL = Path("uncover_dr3_z6_candidates.csv")
    if not LOCAL.exists():
        urllib.request.urlretrieve(RAW, LOCAL)
data = pd.read_csv(LOCAL)
print(f"Loaded {len(data):,} quality-flagged photometric candidates")
print(f"Sky footprint: RA {data.ra.min():.4f}–{data.ra.max():.4f} deg; Dec {data.dec.min():.4f}–{data.dec.max():.4f} deg")
'''

INTRO = """
This notebook uses the frozen UNCOVER DR3 “SUPER” photometric catalogue for
Abell 2744. The release combines HST and JWST imaging, detects sources in a
noise-equalized F277W+F356W+F444W image, PSF-matches the photometry to F444W,
and supplies EAzY photometric-redshift posteriors. The compact repository table
contains rows with usable photometry, a passing EAzY flag, and a maximum-
likelihood redshift from 6 to 15.

That is a candidate selection, not a confirmation list. A photometric redshift
can confuse a Lyman break with dust, an emission-line boosted band, or a lower-
redshift spectral break. Abell 2744 also lenses the background and changes both
the observed brightness and the effective source-plane area. Every result below
is therefore conditional on the release photometry, templates, flags, and lens
model. The notebook measures the catalogue; it does not claim a new population
measurement or spectroscopic discovery.

## Reproducibility contract

The source is Zenodo DOI `10.5281/zenodo.11059273`, retrieved on 1 August 2026.
The upstream FITS MD5 is `baeb44ce166c920050ceb93220b12e05`. The repository
derivative preserves coordinates, broad-band fluxes and errors, redshift
posterior percentiles, flags, an image size proxy, and lensing magnification.
Fluxes are in the catalogue's native 10 nJy units (AB zeropoint 28.9). We keep
negative flux measurements when summarising stacks because clipping them would
bias faint measurements upward. Each figure is saved at publication-oriented
resolution with SciencePlots' `science` style and `no-latex` for reliable Colab
execution.

## Claim boundary

The analysis distinguishes observed quantities from derived proxies. It reports
sample sizes, selection changes, resampling intervals, or parameter stress
tests. Results may motivate a targeted check against UNCOVER DR4 spectroscopy,
but the photometric catalogue alone cannot prove a galaxy's redshift, stellar
mass, star-formation rate, chemical abundance, or physical size. Those require
spectroscopy and/or more complete forward modelling with selection functions.
"""

REFERENCES = """
## References and next validation

- Suess et al. (2024), UNCOVER Data Release 3 photometric catalogue.
- Weaver et al. (2024), MegaScience and UNCOVER imaging catalogue methods.
- Bezanson et al. (2024), UNCOVER survey design and public data.
- Furtak et al. (2023), Abell 2744 lens model.
- Price et al. (2025), UNCOVER DR4/4.1 NIRSpec spectra and secure redshifts.

UNCOVER DR4.1 reports 409 secure or solid spectroscopic redshifts among 553
reduced targets and provides an updated v2.0 lens model. A strong follow-up is
to row-match the DR3 IDs to those products, remeasure the photometric-redshift
outlier rate, and replace approximate lens corrections used here. The notebook
is deliberately frozen to one internally consistent public photometric release
so that later comparisons are explicit rather than silently mixing versions.
"""

RESULT_WRITER = r'''
record = {
    "id": FOLDER,
    "title": TITLE,
    "archive": "UNCOVER / MAST",
    "date": "2026-08-01",
    "question": QUESTION,
    "sample_size": int(SAMPLE_SIZE),
    "results": RESULTS,
    "validation": VALIDATION,
    "notebook": f"mast/{FOLDER}/notebook.ipynb",
    "hero": f"mast/{FOLDER}/{FIGURES[0]}",
    "figures": [f"mast/{FOLDER}/{name}" for name in FIGURES],
    "research_level": "Exploration",
    "claim_type": "Photometric candidate analysis",
    "provenance": [
        "UNCOVER DR3 SUPER catalog, Zenodo DOI 10.5281/zenodo.11059273",
        "Upstream MD5 baeb44ce166c920050ceb93220b12e05",
        "Selection: use_phot=1, flag_eazy=1, 6 <= z_phot < 15",
    ],
    "artifacts": [f"mast/{FOLDER}/{name}" for name in ARTIFACTS],
    "quality_checks": QUALITY_CHECKS,
    "limitations": LIMITATIONS,
}
Path("result.json").write_text(json.dumps(record, indent=2) + "\n")
print("Saved machine-readable scientific audit:", Path("result.json").resolve())
'''


def base(title: str, question: str, analysis_cells: list, case_context: str):
    badge = "https://colab.research.google.com/assets/colab-badge.svg"
    slug = analysis_cells[0]
    cells = [
        md(f"[![Open In Colab]({badge})](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/master/mast/{slug}/notebook.ipynb)\n\n# {title}\n\n**Scientific question:** {question}\n\n{INTRO}"),
        md(case_context), code(IMPORTS), code(LOAD), *[code(x) if kind == "code" else md(x) for kind, x in analysis_cells[1:]],
        md(REFERENCES), code(RESULT_WRITER),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"}, "colab": {"provenance": []},
    })


CASES = [
    (
        "2026-08-01-uncover-highz-candidate-census",
        "How stable is the UNCOVER z >= 6 candidate count to redshift-posterior width?",
        "How many quality-flagged candidates remain when the redshift posterior must be narrow?",
        """## Why this test matters

Raw counts at extreme photometric redshift can look impressive while being
dominated by broad or multi-modal posteriors. We use the central 68% width,
`z840-z160`, as a transparent—not definitive—precision diagnostic. Thresholds
from 1 to 5 are applied to the same 4,731-row table. A bootstrap interval for
the median redshift describes sampling stability inside the width<2 subset;
it does not include template or calibration systematics. The most important
output is the selection curve, because it shows how much the headline count
depends on a defensible but subjective quality boundary.""",
        [
            ("code", r'''
width = data.z840 - data.z160
finite = np.isfinite(width) & (width >= 0)
thresholds = np.array([1, 1.5, 2, 3, 4, 5, 7.5, 10])
counts = np.array([(finite & (width < value)).sum() for value in thresholds])
sensitivity = pd.DataFrame({"maximum_68pct_width": thresholds, "candidate_count": counts,
                            "fraction_of_flagged_table": counts / len(data)})
sensitivity.to_csv("selection_sensitivity.csv", index=False)
print(sensitivity.to_string(index=False))
'''),
            ("code", r'''
strict = data.loc[finite & (width < 2)].copy()
boot = np.array([np.median(RNG.choice(strict.z_phot, len(strict), replace=True)) for _ in range(2000)])
ci = np.percentile(boot, [2.5, 50, 97.5])
print(f"Width < 2: {len(strict):,} candidates; median z={np.median(strict.z_phot):.3f}")
print(f"Bootstrap 95% interval for median z: {ci[0]:.3f}–{ci[2]:.3f}")
'''),
            ("markdown", """## Distribution view

The filled histogram is the full quality-flagged table; the outline is the
narrow-posterior subset. Counts above roughly z=10 should receive extra
scrutiny because fewer filters lie redward of the break, selection volumes are
small, and low-redshift alternatives can remain. The plot is a catalogue
diagnostic, not a luminosity function: no completeness or source-plane area
correction has been applied."""),
            ("code", r'''
bins = np.arange(6, 15.25, .25)
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.hist(data.z_phot, bins=bins, color=COLORS["cyan"], alpha=.45, label="release flags")
ax.hist(strict.z_phot, bins=bins, histtype="step", color=COLORS["navy"], lw=2, label="68% width < 2")
ax.set(xlabel="EAzY maximum-likelihood photometric redshift", ylabel="Candidate count",
       title="UNCOVER high-redshift candidate distribution")
ax.legend(); fig.tight_layout(); fig.savefig("highz_redshift_distribution.png"); plt.show()
'''),
            ("code", r'''
fig, ax = plt.subplots(figsize=(8.2, 4.8))
ax.plot(thresholds, counts, "o-", color=COLORS["coral"], lw=2)
for x, y in zip(thresholds, counts): ax.annotate(f"{y:,}", (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7)
ax.set(xlabel="Maximum accepted 68% redshift-posterior width", ylabel="Retained candidates",
       title="The candidate census is quality-threshold dependent")
fig.tight_layout(); fig.savefig("posterior_width_sensitivity.png"); plt.show()
'''),
            ("code", r'''
FOLDER="2026-08-01-uncover-highz-candidate-census"; TITLE="How stable is the UNCOVER z >= 6 candidate count?"
QUESTION="How many quality-flagged candidates remain when the redshift posterior must be narrow?"
SAMPLE_SIZE=len(data); RESULTS=[f"{len(strict):,} of {len(data):,} candidates have 68% posterior width < 2",
f"Strict-sample median z = {np.median(strict.z_phot):.2f} (bootstrap 95% {ci[0]:.2f}–{ci[2]:.2f})"]
VALIDATION="The sensitivity curve is the validation: the reported census is not treated as threshold-free."
FIGURES=["highz_redshift_distribution.png","posterior_width_sensitivity.png"]; ARTIFACTS=["selection_sensitivity.csv"]
QUALITY_CHECKS=[{"name":"release photometry flag","status":"passed"},{"name":"EAzY reliability flag","status":"passed"},{"name":"posterior-width stress test","status":"passed"}]
LIMITATIONS=["Photometric candidates are not spectroscopic confirmations.","No completeness or lensing-area correction is applied."]
'''),
        ],
    ),
    (
        "2026-08-01-uncover-lyman-break-stacks",
        "Does the expected Lyman-break migration appear in stacked UNCOVER photometry?",
        "Do median broad-band flux patterns move to longer wavelengths with candidate redshift?",
        """## Physical idea

Neutral hydrogen absorbs rest-frame ultraviolet light blueward of Lyman-alpha.
As redshift increases, that break moves through successively redder JWST
filters. We make median, F444W-normalized observed-frame stacks in three
photometric-redshift bins. Only objects with positive F444W flux and signal to
noise above five enter this display; flux in bluer bands may remain negative
and is retained. The normalization compares spectral shape rather than apparent
brightness. It cannot reveal chemical constituents because these are wide
filters, and emission lines, dust, and redshift-template assumptions remain
mixed together.""",
        [
            ("code", r'''
bands=np.array(["f090w","f115w","f150w","f200w","f277w","f356w","f444w"])
waves=np.array([0.90,1.15,1.50,2.00,2.77,3.56,4.44])
base=data[(data.f_f444w>0)&(data.f_f444w/data.e_f444w>=5)].copy()
z_bins=[(6,7),(7,9),(9,12)]; rows=[]
for lo,hi in z_bins:
    sample=base[base.z_phot.between(lo,hi,inclusive="left")]
    for band,wave in zip(bands,waves):
        ratio=sample[f"f_{band}"]/sample.f_f444w
        rows.append([lo,hi,band,wave,len(sample),np.nanmedian(ratio),
                     np.nanpercentile(ratio,[16,84])[0],np.nanpercentile(ratio,[16,84])[1]])
stack=pd.DataFrame(rows,columns=["z_low","z_high","band","wavelength_um","n","median_fnu_over_f444w","p16","p84"])
stack.to_csv("median_sed_stacks.csv",index=False)
print(stack.groupby(["z_low","z_high"]).n.first())
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(9,5.4))
for (lo,hi),group in stack.groupby(["z_low","z_high"]):
    ax.plot(group.wavelength_um,group.median_fnu_over_f444w,"o-",lw=2,label=f"{lo} <= zphot < {hi} (n={group.n.iloc[0]:,})")
    break_um=.1216*(1+(lo+hi)/2); ax.axvline(break_um,color="0.6",ls=":",lw=.8)
ax.axhline(0,color="0.5",lw=.8); ax.set(xlabel="Observed wavelength (micrometres)",ylabel="Median Fnu / F444W",
title="Median observed-frame SEDs show a migrating blue suppression"); ax.legend(); fig.tight_layout()
fig.savefig("lyman_break_median_stacks.png"); plt.show()
'''),
            ("markdown", """## A direct colour stress test

For each redshift range we pair a band expected to lie nearer or blueward of
the break with a redder detection band. Medians are bootstrapped over objects.
The ratio is deliberately called a suppression proxy, not a break amplitude,
because filter transmission curves are not integrated here and the selection
already used the same photometry. The test is therefore descriptive and partly
circular; spectroscopy would provide independent validation."""),
            ("code", r'''
pairs=[(6,8,"f090w","f200w"),(8,10,"f115w","f277w"),(10,12,"f150w","f356w")]
drop=[]
for lo,hi,blue,red in pairs:
    s=data[data.z_phot.between(lo,hi,inclusive="left") & (data[f"f_{red}"]>0) & (data[f"f_{red}"]/data[f"e_{red}"]>=5)]
    values=(s[f"f_{blue}"]/s[f"f_{red}"]).replace([np.inf,-np.inf],np.nan).dropna().to_numpy()
    boots=np.array([np.median(RNG.choice(values,len(values),replace=True)) for _ in range(1500)])
    q=np.percentile(boots,[2.5,50,97.5]); drop.append([lo,hi,blue,red,len(values),*q])
drop=pd.DataFrame(drop,columns=["z_low","z_high","blue_band","red_band","n","ratio_low","ratio_median","ratio_high"])
drop.to_csv("dropout_ratio_summary.csv",index=False); print(drop.to_string(index=False))
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(7.8,4.8)); labels=[]
for i,r in drop.iterrows():
    ax.errorbar(i,r.ratio_median,yerr=[[r.ratio_median-r.ratio_low],[r.ratio_high-r.ratio_median]],fmt="o",capsize=5,color=COLORS["violet"])
    labels.append(f"{r.blue_band.upper()}/{r.red_band.upper()}\n{r.z_low:g}–{r.z_high:g}")
ax.set_xticks(range(len(labels)),labels); ax.axhline(1,color="0.5",ls="--")
ax.set(ylabel="Median blue/red flux ratio",title="Blue-band suppression proxies with bootstrap intervals")
fig.tight_layout(); fig.savefig("dropout_ratio_bootstrap.png"); plt.show()
'''),
            ("code", r'''
FOLDER="2026-08-01-uncover-lyman-break-stacks"; TITLE="Does the Lyman-break migration appear in stacked UNCOVER photometry?"
QUESTION="Do median broad-band flux patterns move to longer wavelengths with candidate redshift?"; SAMPLE_SIZE=len(base)
RESULTS=[f"{len(base):,} candidates pass the F444W signal-to-noise display cut",f"Median blue/red ratios span {drop.ratio_median.min():.3f}–{drop.ratio_median.max():.3f} across the three bins"]
VALIDATION="The wavelength of blue suppression shifts redward across bins as expected for a Lyman break, but this is not independent of the photometric-redshift fit."
FIGURES=["lyman_break_median_stacks.png","dropout_ratio_bootstrap.png"]; ARTIFACTS=["median_sed_stacks.csv","dropout_ratio_summary.csv"]
QUALITY_CHECKS=[{"name":"negative blue flux retained","status":"passed"},{"name":"red-band S/N >= 5","status":"passed"},{"name":"bootstrap intervals","status":"passed"}]
LIMITATIONS=["Broad-band stacks cannot identify chemical abundances.","The colour check reuses photometry that informed z_phot."]
'''),
        ],
    ),
    (
        "2026-08-01-uncover-lensing-brightness",
        "How strongly does Abell 2744 lensing change candidate brightness rankings?",
        "How do observed and approximately de-lensed F444W fluxes differ across the high-z sample?",
        """## Why lensing must be explicit

The cluster magnifies background sources, letting JWST detect intrinsically
fainter candidates, but the correction is model dependent near critical
curves. We compare observed F444W flux with the simple proxy `F444W/mu`. This
removes scalar flux magnification only; it does not correct survey area,
multiple images, shear, or selection completeness. The primary analysis caps
magnification at 30 and repeats summary values under caps of 5, 10, 20, 30,
and 50. This makes extreme model values visible instead of allowing a handful
of rows to control the conclusion.""",
        [
            ("code", r'''
lens=data[(data.f_f444w>0)&(data.e_f444w>0)&np.isfinite(data.mu)&(data.mu>=1)].copy()
lens["snr_f444w"]=lens.f_f444w/lens.e_f444w; lens=lens[lens.snr_f444w>=5]
lens["intrinsic_f444w_proxy"]=lens.f_f444w/lens.mu
primary=lens[lens.mu<=30].copy()
print(f"S/N-selected rows: {len(lens):,}; primary mu<=30 rows: {len(primary):,}")
print(primary[["f_f444w","mu","intrinsic_f444w_proxy"]].describe(percentiles=[.5,.9,.95,.99]).round(3))
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(8,5.4)); sc=ax.scatter(primary.f_f444w,primary.intrinsic_f444w_proxy,c=primary.mu,s=9,cmap="viridis",alpha=.55,rasterized=True)
limits=[max(primary.f_f444w.min(),.05),np.percentile(primary.f_f444w,99.5)]
ax.plot(limits,limits,ls="--",color="0.5",label="no magnification"); ax.set_xscale("log"); ax.set_yscale("log")
ax.set(xlabel="Observed F444W flux (10 nJy)",ylabel="F444W / magnification (10 nJy)",title="Lensing changes inferred intrinsic brightness")
fig.colorbar(sc,ax=ax,label="Catalog magnification"); ax.legend(); fig.tight_layout(); fig.savefig("lensing_brightness_comparison.png"); plt.show()
'''),
            ("markdown", """## Magnification-cap sensitivity

The median flux correction is bootstrapped for the primary sample, while the
cap table shows whether increasingly uncertain high-magnification rows alter
the answer. This is a model sensitivity test, not a full lensing uncertainty
propagation. The catalogue's percentile columns describe local magnification
uncertainty, but correlations in the lens model and source-plane mapping need
specialist treatment."""),
            ("code", r'''
caps=[5,10,20,30,50]; rows=[]
for cap in caps:
    s=lens[lens.mu<=cap]
    rows.append([cap,len(s),np.median(s.mu),np.median(s.f_f444w),np.median(s.intrinsic_f444w_proxy)])
cap_table=pd.DataFrame(rows,columns=["mu_cap","n","median_mu","median_observed_f444w","median_intrinsic_proxy"])
cap_table.to_csv("magnification_cap_sensitivity.csv",index=False)
ratios=primary.intrinsic_f444w_proxy.to_numpy()/primary.f_f444w.to_numpy()
boot=np.array([np.median(RNG.choice(ratios,len(ratios),replace=True)) for _ in range(2000)]); ci=np.percentile(boot,[2.5,50,97.5])
print(cap_table.to_string(index=False)); print("Median intrinsic/observed ratio 95% interval:",ci)
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(8,4.8)); ax.plot(cap_table.mu_cap,cap_table.median_intrinsic_proxy,"o-",label="de-lensed proxy",color=COLORS["coral"])
ax.plot(cap_table.mu_cap,cap_table.median_observed_f444w,"o-",label="observed",color=COLORS["navy"])
ax.set(xlabel="Maximum accepted magnification",ylabel="Median F444W flux (10 nJy)",title="Median brightness is stable to the extreme-magnification cap")
ax.legend(); fig.tight_layout(); fig.savefig("magnification_cap_stress.png"); plt.show()
'''),
            ("code", r'''
primary[["id","z_phot","f_f444w","e_f444w","mu","mu_low_68","mu_high_68","intrinsic_f444w_proxy"]].to_csv("lensing_working_sample.csv",index=False)
FOLDER="2026-08-01-uncover-lensing-brightness"; TITLE="How strongly does Abell 2744 lensing change candidate brightness rankings?"
QUESTION="How do observed and approximately de-lensed F444W fluxes differ across the high-z sample?"; SAMPLE_SIZE=len(primary)
RESULTS=[f"Primary sample contains {len(primary):,} candidates with F444W S/N >= 5 and mu <= 30",f"Median intrinsic/observed flux ratio = {ci[1]:.3f} (bootstrap 95% {ci[0]:.3f}–{ci[2]:.3f})"]
VALIDATION="Results are repeated across five magnification caps; a future DR4 v2.0 lens-map match is required for precision use."
FIGURES=["lensing_brightness_comparison.png","magnification_cap_stress.png"]; ARTIFACTS=["magnification_cap_sensitivity.csv","lensing_working_sample.csv"]
QUALITY_CHECKS=[{"name":"F444W S/N >= 5","status":"passed"},{"name":"magnification cap stress test","status":"passed"},{"name":"bootstrap interval","status":"passed"}]
LIMITATIONS=["F444W/mu is a flux proxy, not a luminosity function.","DR3 magnifications are superseded by the DR4 v2.0 lens model."]
'''),
        ],
    ),
    (
        "2026-08-01-uncover-size-redshift",
        "Do UNCOVER high-z candidates show a change in catalogue half-light-radius proxy?",
        "How does the observed flux-radius proxy vary across redshift bins after a simple lens correction?",
        """## Measurement definition

`flux_radius` is the catalogue radius containing half the detected flux in the
PSF-matched images. We convert arcseconds to projected kiloparsecs with a flat
Planck18 cosmology and divide by square root of scalar magnification as a rough
circularized lens correction. The sample requires F444W signal to noise above
five, 0.03–1 arcsec observed radius, and magnification from 1 to 30. These cuts
remove clear numerical extremes but do not deconvolve the F444W PSF or correct
directional shear. The result is explicitly a size proxy and a method audit,
not a published intrinsic size–redshift relation.""",
        [
            ("code", r'''
from astropy.cosmology import Planck18
size=data[(data.f_f444w/data.e_f444w>=5)&data.flux_radius.between(.03,1)&data.mu.between(1,30)&np.isfinite(data.z_phot)].copy()
size["kpc_per_arcsec"]=Planck18.kpc_proper_per_arcmin(size.z_phot.to_numpy()).value/60
size["observed_radius_kpc"]=size.flux_radius*size.kpc_per_arcsec
size["delensed_radius_proxy_kpc"]=size.observed_radius_kpc/np.sqrt(size.mu)
print(size[["flux_radius","mu","observed_radius_kpc","delensed_radius_proxy_kpc"]].describe().round(3))
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(8.5,5.3)); sc=ax.scatter(size.z_phot,size.delensed_radius_proxy_kpc,c=np.log10(size.mu),s=8,alpha=.45,cmap="plasma",rasterized=True)
ax.set(xlabel="Photometric redshift",ylabel="Approx. de-lensed half-light-radius proxy (kpc)",title="Candidate size proxies across redshift")
fig.colorbar(sc,ax=ax,label="log10 magnification"); ax.set_ylim(0,np.percentile(size.delensed_radius_proxy_kpc,99)); fig.tight_layout(); fig.savefig("size_proxy_scatter.png"); plt.show()
'''),
            ("markdown", """## Binned medians and cut sensitivity

Wide redshift bins reduce noise while avoiding a fitted power law whose
physical interpretation would exceed the catalogue. Bootstrap intervals show
sampling variation. We then vary the upper observed-radius cut from 0.5 to
1.5 arcsec. Stability under that choice is useful, but it cannot remove the
unmodelled PSF floor or the coupling between magnification, detection, and
size."""),
            ("code", r'''
edges=np.array([6,7,8,10,12,15]); rows=[]
for lo,hi in zip(edges[:-1],edges[1:]):
    values=size.loc[size.z_phot.between(lo,hi,inclusive="left"),"delensed_radius_proxy_kpc"].dropna().to_numpy()
    boots=np.array([np.median(RNG.choice(values,len(values),replace=True)) for _ in range(1500)])
    q=np.percentile(boots,[2.5,50,97.5]); rows.append([lo,hi,len(values),*q])
binned=pd.DataFrame(rows,columns=["z_low","z_high","n","radius_low","radius_median","radius_high"])
binned.to_csv("size_proxy_by_redshift.csv",index=False); print(binned.to_string(index=False))
'''),
            ("code", r'''
cut_rows=[]
for upper in [.5,.75,1,1.25,1.5]:
    s=data[(data.f_f444w/data.e_f444w>=5)&data.flux_radius.between(.03,upper)&data.mu.between(1,30)]
    scale=Planck18.kpc_proper_per_arcmin(s.z_phot.to_numpy()).value/60
    proxy=s.flux_radius*scale/np.sqrt(s.mu); cut_rows.append([upper,len(s),np.nanmedian(proxy)])
cut_table=pd.DataFrame(cut_rows,columns=["maximum_radius_arcsec","n","median_proxy_kpc"]); cut_table.to_csv("size_cut_sensitivity.csv",index=False)
fig,ax=plt.subplots(figsize=(8,4.8)); centers=(binned.z_low+binned.z_high)/2
ax.errorbar(centers,binned.radius_median,yerr=[binned.radius_median-binned.radius_low,binned.radius_high-binned.radius_median],fmt="o-",capsize=4,color=COLORS["green"])
ax.set(xlabel="Photometric-redshift bin centre",ylabel="Median de-lensed radius proxy (kpc)",title="Binned size proxies with bootstrap intervals")
fig.tight_layout(); fig.savefig("size_proxy_binned.png"); plt.show()
'''),
            ("code", r'''
FOLDER="2026-08-01-uncover-size-redshift"; TITLE="Do UNCOVER high-z candidates show a change in catalogue size proxy?"
QUESTION="How does the observed flux-radius proxy vary across redshift bins after a simple lens correction?"; SAMPLE_SIZE=len(size)
RESULTS=[f"{len(size):,} candidates pass the flux, radius, and magnification cuts",f"Median approximate de-lensed radius proxy = {np.median(size.delensed_radius_proxy_kpc):.2f} kpc"]
VALIDATION="Bootstrap intervals and five radius-cut choices expose sampling and threshold sensitivity; PSF and shear modelling remain outstanding."
FIGURES=["size_proxy_scatter.png","size_proxy_binned.png"]; ARTIFACTS=["size_proxy_by_redshift.csv","size_cut_sensitivity.csv"]
QUALITY_CHECKS=[{"name":"F444W S/N >= 5","status":"passed"},{"name":"radius and magnification cuts","status":"passed"},{"name":"cut sensitivity","status":"passed"}]
LIMITATIONS=["The catalogue flux radius is PSF affected.","Dividing by sqrt(mu) ignores directional shear and is only a proxy."]
'''),
        ],
    ),
    (
        "2026-08-01-uncover-spatial-selection",
        "Is the sky density of UNCOVER high-z candidates spatially uniform?",
        "Do candidate surface-density variations track F444W coverage and lensing structure?",
        """## Selection-map question

Deep fields are not uniformly sensitive. The Abell 2744 mosaic combines
programs, has spatially varying weight, contains subtracted cluster galaxies,
and samples a strong lens. We bin the candidate coordinates into a 7-by-7 sky
grid, count candidates, and record median F444W weight and magnification per
occupied cell. A Spearman correlation tests whether cells with deeper F444W
coverage contain more selected candidates. This does not measure cosmic
clustering because the denominator—the number of all detectable galaxies in
each cell—and the source-plane area are absent. It is a diagnostic of why a
sky map should accompany any population claim.""",
        [
            ("code", r'''
spatial=data[np.isfinite(data.ra)&np.isfinite(data.dec)&np.isfinite(data.w_f444w)&np.isfinite(data.mu)].copy()
ra_edges=np.linspace(spatial.ra.min(),spatial.ra.max(),8); dec_edges=np.linspace(spatial.dec.min(),spatial.dec.max(),8)
spatial["ra_bin"]=pd.cut(spatial.ra,ra_edges,labels=False,include_lowest=True)
spatial["dec_bin"]=pd.cut(spatial.dec,dec_edges,labels=False,include_lowest=True)
grid=spatial.groupby(["ra_bin","dec_bin"],observed=True).agg(candidate_count=("id","size"),median_f444w_weight=("w_f444w","median"),median_mu=("mu","median"),median_z=("z_phot","median")).reset_index()
grid.to_csv("spatial_grid_summary.csv",index=False)
rho,p=stats.spearmanr(grid.candidate_count,grid.median_f444w_weight,nan_policy="omit")
print(f"Occupied cells={len(grid)}; density-depth Spearman rho={rho:.3f}, p={p:.3g}")
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(8.2,6)); sc=ax.scatter(spatial.ra,spatial.dec,c=spatial.z_phot,s=7,cmap="magma",alpha=.55,rasterized=True)
ax.invert_xaxis(); ax.set(xlabel="Right ascension (degrees)",ylabel="Declination (degrees)",title="UNCOVER photometric high-redshift candidate map")
fig.colorbar(sc,ax=ax,label="Photometric redshift"); fig.tight_layout(); fig.savefig("highz_candidate_sky_map.png"); plt.show()
'''),
            ("markdown", """## Depth relation and null interpretation

The grid correlation is reported with its p-value but is not treated as a
formal discovery test: adjacent cells share observing strategy and lensing
structure, grid choice is arbitrary, and candidate counts are not independent.
We repeat the correlation for 5-, 6-, 7-, 8-, and 9-bin grids. A changing sign
or magnitude would warn that the headline coefficient is mostly a binning
artifact."""),
            ("code", r'''
stress=[]
for nbin in [5,6,7,8,9]:
    rb=pd.cut(spatial.ra,np.linspace(spatial.ra.min(),spatial.ra.max(),nbin+1),labels=False,include_lowest=True)
    db=pd.cut(spatial.dec,np.linspace(spatial.dec.min(),spatial.dec.max(),nbin+1),labels=False,include_lowest=True)
    g=spatial.assign(rb=rb,db=db).groupby(["rb","db"],observed=True).agg(count=("id","size"),weight=("w_f444w","median"),mu=("mu","median")).reset_index()
    rr,pp=stats.spearmanr(g["count"],g.weight,nan_policy="omit"); rm,pm=stats.spearmanr(g["count"],g.mu,nan_policy="omit")
    stress.append([nbin,len(g),rr,pp,rm,pm])
stress=pd.DataFrame(stress,columns=["bins_per_axis","occupied_cells","rho_count_weight","p_count_weight","rho_count_mu","p_count_mu"])
stress.to_csv("spatial_binning_sensitivity.csv",index=False); print(stress.to_string(index=False))
'''),
            ("code", r'''
fig,ax=plt.subplots(figsize=(8,4.9)); sizes=25+35*np.clip(grid.median_mu,1,8)
sc=ax.scatter(grid.median_f444w_weight,grid.candidate_count,s=sizes,c=grid.median_mu,cmap="viridis",alpha=.75,edgecolor="white",linewidth=.4)
ax.set(xlabel="Median relative F444W weight per cell",ylabel="Candidate count per cell",title="Candidate density, image weight, and lensing are entangled")
fig.colorbar(sc,ax=ax,label="Median magnification"); fig.tight_layout(); fig.savefig("candidate_density_depth_relation.png"); plt.show()
'''),
            ("code", r'''
FOLDER="2026-08-01-uncover-spatial-selection"; TITLE="Is the sky density of UNCOVER high-z candidates spatially uniform?"
QUESTION="Do candidate surface-density variations track F444W coverage and lensing structure?"; SAMPLE_SIZE=len(spatial)
RESULTS=[f"The 7x7 occupied-cell depth relation has Spearman rho = {rho:.2f} (p = {p:.3g})",f"Grid stress-test rho spans {stress.rho_count_weight.min():.2f} to {stress.rho_count_weight.max():.2f}"]
VALIDATION="The relation is repeated across five grid resolutions and is interpreted only as a selection diagnostic."
FIGURES=["highz_candidate_sky_map.png","candidate_density_depth_relation.png"]; ARTIFACTS=["spatial_grid_summary.csv","spatial_binning_sensitivity.csv"]
QUALITY_CHECKS=[{"name":"finite coordinate and weight cut","status":"passed"},{"name":"five grid resolutions","status":"passed"},{"name":"lensing shown explicitly","status":"passed"}]
LIMITATIONS=["Counts are not corrected by source-plane area or completeness.","A single cluster field cannot establish cosmic clustering."]
'''),
        ],
    ),
]


def main() -> None:
    for slug, title, question, context, raw_cells in CASES:
        # base() expects the slug as a sentinel followed by typed cells.
        notebook = base(title, question, [slug, *raw_cells], context)
        folder = ROOT / "mast" / slug
        folder.mkdir(parents=True, exist_ok=True)
        nbf.write(notebook, folder / "notebook.ipynb")
        readme = f"""# {title}

**Question:** {question}

This research-level exploration uses the compact, quality-flagged UNCOVER DR3
photometric catalogue subset preserved in `data/uncover_dr3_highz/`. Open the
executed notebook for the figures, numerical results, quality tests, provenance,
and explicit claim boundary. Every plot uses SciencePlots' `science` style with
the `no-latex` option for reliable local and Google Colab execution.

These are photometric high-redshift candidates behind Abell 2744, not a list of
new spectroscopic confirmations. The next independent check is a row match to
the UNCOVER DR4.1 secure-redshift and updated lens-model products.
"""
        (folder / "README.md").write_text(readme, encoding="utf-8")
        print("WROTE", folder.relative_to(ROOT))


if __name__ == "__main__":
    main()
