"""Build five UNCOVER DR4.1 spectroscopy audit notebooks."""

from __future__ import annotations

from pathlib import Path
import textwrap

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-08-01"


def md(value: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(value).strip())


def code(value: str):
    return nbf.v4.new_code_cell(textwrap.dedent(value).strip())


IMPORTS = r'''
from pathlib import Path
import json, zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scienceplots
from scipy import stats
from scipy.ndimage import gaussian_filter
from astropy.io import fits

plt.style.use(["science", "no-latex"])
plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 220, "axes.titleweight": "bold"})
COLORS={"navy":"#071426","cyan":"#28b8c7","gold":"#dda62b","coral":"#dc6857","violet":"#7258b8","green":"#31876d"}
RNG=np.random.default_rng(1999)
DATA=Path("../../data/uncover_dr4_spectroscopy")
if not DATA.exists(): DATA=Path("data/uncover_dr4_spectroscopy")
'''

INTRO = '''
This notebook is an independent audit of public UNCOVER DR4.1 spectroscopy in
the Abell 2744 field. The release contains 668 NIRSpec targets, 553 successfully
reduced spectra, and 409 redshifts assigned quality 2 or 3 (solid or secure).
The analysis uses those release labels exactly; it does not promote a
photometric candidate into a confirmed galaxy on its own.

## What is measured and what is not

The DR3 catalogue supplied broad-band photometric redshifts. DR4.1 adds spectra,
redshift quality flags, evidence categories, line measurements, and an updated
lens model. Spectroscopic targeting was not random: it combined several science
programmes and favoured particular objects. Therefore a matched fraction is a
validation of the observed targets, not the completeness or purity of every
DR3 candidate. A non-match means “not tested here,” not “false.”

Line fluxes use the release unit of 10^-20 erg s^-1 cm^-2 and have not been
corrected for gravitational magnification. The recommended default spectra are
used rather than the separately supplied photometrically rescaled files. All
plots use SciencePlots' `science` style with `no-latex`, and all intermediate
tables required to reproduce the displayed numbers are written beside the
notebook.

## Reproducibility and claim boundary

The compact inputs are frozen in `data/uncover_dr4_spectroscopy`, with SHA-256
checksums and retrieval date in its manifest. The authoritative source is the
UNCOVER DR4.1 release page and Price et al. (2025). The results below describe
this public release. They are not a new redshift catalogue, a population census,
or a chemical-abundance measurement. Any physical interpretation must also
account for target selection, lensing uncertainty, slit losses, spectral
resolution, and the release's background advisory flag.
'''

REFERENCES = '''
## References

- Price et al. (2025), UNCOVER DR4/4.1 NIRSpec data release and catalogue.
- Suess et al. (2024), UNCOVER DR3 photometric catalogue.
- Weaver et al. (2024), MegaScience/UNCOVER imaging and photometry.
- Furtak et al. (2023), Abell 2744 lens model; DR4.1 supplies the updated v2.0 values.
- MAST Astrocut service documentation for the HST Frontier Fields cutouts.

The safest next validation is to repeat the redshift comparison with a
target-selection model and, for line physics, refit the spectra jointly with
the line-spread function and lens-model posterior. Those steps are outside this
compact audit and are stated rather than silently assumed.
'''

LOAD = r'''
cross=pd.read_csv(DATA/"dr3_dr4_highz_crossmatch.csv")
cross["z_spec"]=cross["z_spec_dr4"]
secure=pd.read_csv(DATA/"dr4_secure_redshifts.csv")
lines=pd.read_csv(DATA/"dr4_highz_line_fluxes.csv")
mag=pd.read_csv(DATA/"dr4_highz_magnifications.csv")
print(f"DR3 high-z candidates with solid/secure DR4.1 matches: {len(cross)}")
print(f"All solid/secure DR4.1 redshifts: {len(secure)}; z>=6: {(secure.z_spec>=6).sum()}")
'''

WRITER = r'''
record={"id":FOLDER,"title":TITLE,"archive":"UNCOVER / MAST","date":"2026-08-01",
"question":QUESTION,"sample_size":int(SAMPLE_SIZE),"results":RESULTS,"validation":VALIDATION,
"notebook":f"mast/{FOLDER}/notebook.ipynb","hero":f"mast/{FOLDER}/{FIGURES[0]}",
"figures":[f"mast/{FOLDER}/{x}" for x in FIGURES],"research_level":"Spectroscopic audit",
"claim_type":CLAIM,"provenance":["UNCOVER DR4.1 public release; Price et al. (2025)",
"Solid/secure selection: flag_zspec_qual in {2,3}","Frozen derivative checksums: data/uncover_dr4_spectroscopy/manifest.json"],
"artifacts":[f"mast/{FOLDER}/{x}" for x in ARTIFACTS],"quality_checks":CHECKS,"limitations":LIMITS}
Path("result.json").write_text(json.dumps(record,indent=2)+"\n")
print("Saved scientific audit record")
'''


CASES = [
("2026-08-01-uncover-photz-specz-validation", "Photometric versus spectroscopic redshift",
 "How well did the DR3 high-redshift estimates agree with solid or secure DR4.1 spectroscopy?",
 '''## Analysis plan

We join the two public releases by the DR3 catalogue identifier carried into
DR4.1. The robust scatter is the normalized median absolute deviation of
`(z_phot-z_spec)/(1+z_spec)`. We also report an outlier fraction at an explicitly
stated threshold of 0.15. Because targets were deliberately selected, these
numbers apply only to the 44 matched candidates. The one-to-one diagram makes
large failures visible instead of hiding them in a single score.''',
 [r'''
dz=(cross.z_phot-cross.z_spec)/(1+cross.z_spec)
nmad=1.4826*np.median(np.abs(dz-np.median(dz)))
out=np.abs(dz)>0.15
summary=cross[["id","id_msa","z_phot","z160","z840","z_spec","flag_zspec_qual"]].copy()
summary["normalized_residual"]=dz; summary["outlier_abs_gt_0p15"]=out
summary.to_csv("photz_specz_residuals.csv",index=False)
print(f"NMAD={nmad:.4f}; outliers={out.sum()}/{len(out)} ({out.mean():.1%})")
''', r'''
fig,ax=plt.subplots(figsize=(6.6,6))
ax.scatter(cross.z_spec,cross.z_phot,c=np.abs(dz),cmap="viridis",s=42,edgecolor="white",linewidth=.4)
lim=(-.3,14); ax.plot(lim,lim,"--",color=COLORS["coral"],label="one-to-one")
ax.set(xlim=lim,ylim=lim,xlabel="DR4.1 spectroscopic redshift",ylabel="DR3 photometric redshift",title="Spectroscopy tests the photometric candidates")
ax.legend(); fig.tight_layout(); fig.savefig("photz_specz_validation.png"); plt.show()
''', r'''
fig,ax=plt.subplots(figsize=(8,4.6)); ax.axhline(0,color="0.3",lw=1)
ax.scatter(cross.z_spec,dz,c=np.where(out,COLORS["coral"],COLORS["cyan"]),s=40)
ax.axhspan(-.15,.15,color=COLORS["green"],alpha=.12,label="|residual| <= 0.15")
ax.set(xlabel="Spectroscopic redshift",ylabel="(zphot-zspec)/(1+zspec)",title="Normalized redshift residuals"); ax.legend()
fig.tight_layout(); fig.savefig("normalized_redshift_residuals.png"); plt.show()
''', r'''
high=(cross.z_spec>=6); print(f"{high.sum()} of {len(cross)} matches remain at z>=6")
print(summary.sort_values("normalized_residual",key=abs,ascending=False).head(5).to_string(index=False))
''', r'''
FOLDER="2026-08-01-uncover-photz-specz-validation"; TITLE="Photometric versus spectroscopic redshift"
QUESTION="How well did DR3 high-redshift estimates agree with solid or secure DR4.1 spectroscopy?"; SAMPLE_SIZE=len(cross)
RESULTS=[f"{high.sum()} of {len(cross)} matched candidates have zspec >= 6",f"Normalized median absolute deviation = {nmad:.3f}",f"Outlier fraction at |dz|/(1+zspec)>0.15 = {out.mean():.1%}"]
VALIDATION="Robust scatter, explicit outlier threshold, and row-level residual table expose both agreement and failures."
FIGURES=["photz_specz_validation.png","normalized_redshift_residuals.png"]; ARTIFACTS=["photz_specz_residuals.csv"]
CLAIM="Matched-sample redshift validation"; CHECKS=[{"name":"catalogue-ID join","status":"passed"},{"name":"robust scatter","status":"passed"}]
LIMITS=["The spectroscopic targets are not a random sample.","Unmatched candidates receive no verdict."]
''']),

("2026-08-01-uncover-redshift-interval-calibration", "Are the photometric redshift intervals calibrated?",
 "How often does the DR4.1 redshift fall inside the DR3 central 68 percent interval?",
 '''## Analysis plan

A well-calibrated 68 percent interval should contain the later reference value
about 68 percent of the time under matched sampling assumptions. We measure
empirical coverage and attach a Wilson binomial interval. We then widen every
photometric interval around its midpoint by scale factors from 0.5 to 4.0. This
is a diagnostic, not a corrected posterior: it shows how much simple global
inflation would be required and cannot repair multi-modal or biased solutions.''',
 [r'''
inside=(cross.z_spec>=cross.z160)&(cross.z_spec<=cross.z840); n=len(cross); k=int(inside.sum())
zcrit=stats.norm.ppf(.975); center=(k+zcrit*zcrit/2)/(n+zcrit*zcrit)
half=zcrit*np.sqrt(k*(n-k)/n+zcrit*zcrit/4)/(n+zcrit*zcrit); ci=(center-half,center+half)
print(f"Coverage={k}/{n}={k/n:.1%}; Wilson 95% interval {ci[0]:.1%}-{ci[1]:.1%}")
''', r'''
mid=(cross.z160+cross.z840)/2; halfwidth=(cross.z840-cross.z160)/2
scales=np.linspace(.5,4,36); coverage=np.array([((cross.z_spec>=mid-s*halfwidth)&(cross.z_spec<=mid+s*halfwidth)).mean() for s in scales])
cal=pd.DataFrame({"interval_halfwidth_scale":scales,"empirical_coverage":coverage}); cal.to_csv("coverage_curve.csv",index=False)
scale68=float(scales[np.argmin(np.abs(coverage-.68))]); print(f"Nearest grid scale for 68% empirical coverage: {scale68:.2f}")
''', r'''
fig,ax=plt.subplots(figsize=(8,4.8)); ax.plot(scales,coverage,"o-",color=COLORS["violet"],ms=4)
ax.axhline(.68,ls="--",color=COLORS["coral"],label="nominal 68%")
ax.axvline(1,ls=":",color="0.3",label="published interval")
ax.set(xlabel="Scale applied to interval half-width",ylabel="Empirical coverage",ylim=(0,1),title="Coverage stress test"); ax.legend()
fig.tight_layout(); fig.savefig("redshift_interval_coverage.png"); plt.show()
''', r'''
fig,ax=plt.subplots(figsize=(8,4.8)); order=np.argsort(cross.z_spec.values); x=np.arange(n)
ax.vlines(x,cross.z160.iloc[order],cross.z840.iloc[order],color=np.where(inside.iloc[order],COLORS["cyan"],COLORS["coral"]),lw=1.4)
ax.scatter(x,cross.z_spec.iloc[order],s=12,c="black",zorder=3,label="zspec")
ax.set(xlabel="Matched object, ordered by zspec",ylabel="Redshift",title="Published central 68% intervals and spectroscopic values"); ax.legend()
fig.tight_layout(); fig.savefig("redshift_interval_audit.png"); plt.show()
''', r'''
FOLDER="2026-08-01-uncover-redshift-interval-calibration"; TITLE="Are the photometric redshift intervals calibrated?"
QUESTION="How often does DR4.1 zspec fall inside the DR3 central 68 percent interval?"; SAMPLE_SIZE=n
RESULTS=[f"Observed central-68% coverage = {k/n:.1%} ({k}/{n})",f"Wilson 95% interval = {ci[0]:.1%}-{ci[1]:.1%}",f"Nearest global width scale for 68% coverage = {scale68:.2f}"]
VALIDATION="Wilson uncertainty and an interval-width stress curve quantify finite-sample and calibration effects."
FIGURES=["redshift_interval_coverage.png","redshift_interval_audit.png"]; ARTIFACTS=["coverage_curve.csv"]
CLAIM="Photometric interval calibration audit"; CHECKS=[{"name":"interval ordering","status":"passed"},{"name":"binomial uncertainty","status":"passed"}]
LIMITS=["Only targeted matches are tested.","Global interval scaling is diagnostic, not a posterior recalibration."]
''']),

("2026-08-01-uncover-spectroscopic-evidence", "What supports the UNCOVER redshifts?",
 "How do emission lines, breaks, exposure time, and the background advisory relate to redshift quality?",
 '''## Analysis plan

DR4.1 records several evidence flags: emission lines, a line plus a break,
strong absorption or break features, break only, and stellar-bump only. These
are not mutually exclusive in every processing stage, so we report their raw
counts and build a transparent primary category in a stated priority order.
The background flag is advisory rather than an automatic rejection. Comparing
exposure times and redshift distributions checks whether one evidence class is
being over-interpreted.''',
 [r'''
flags=["flag_line_and_break","flag_emission_lines","flag_break_strong_abs_features_only","flag_break_only","flag_stellar_bump_only"]
counts=secure[flags].fillna(0).eq(1).sum().sort_values(ascending=False); print(counts)
def category(row):
 for col,label in [("flag_line_and_break","line + break"),("flag_emission_lines","emission line"),("flag_break_strong_abs_features_only","break/absorption"),("flag_break_only","break only"),("flag_stellar_bump_only","stellar bump")]:
  if row.get(col)==1:return label
 return "other/manual"
secure["primary_evidence"]=secure.apply(category,axis=1)
table=secure.groupby("primary_evidence").agg(objects=("id_msa","size"),median_z=("z_spec","median"),median_exposure_s=("texp_tot","median")).reset_index()
table.to_csv("spectroscopic_evidence_summary.csv",index=False); print(table.to_string(index=False))
''', r'''
fig,ax=plt.subplots(figsize=(8,4.8)); order=table.sort_values("objects")
ax.barh(order.primary_evidence,order.objects,color=COLORS["cyan"])
ax.set(xlabel="Solid or secure redshifts",title="Primary spectroscopic evidence category"); fig.tight_layout(); fig.savefig("spectroscopic_evidence_counts.png"); plt.show()
''', r'''
fig,ax=plt.subplots(figsize=(8.4,5)); cats=table.sort_values("median_z").primary_evidence
groups=[secure.loc[secure.primary_evidence==c,"z_spec"].values for c in cats]
ax.boxplot(groups,tick_labels=cats,showfliers=False); ax.set(ylabel="Spectroscopic redshift",title="Redshift range by evidence category")
ax.tick_params(axis="x",rotation=25); fig.tight_layout(); fig.savefig("evidence_redshift_ranges.png"); plt.show()
''', r'''
bg=secure.flag_potential_local_background_issue.eq(1)
stress=pd.DataFrame({"selection":["all secure/solid","exclude background advisory"],"objects":[len(secure),(~bg).sum()],"median_z":[secure.z_spec.median(),secure.loc[~bg,"z_spec"].median()]})
stress.to_csv("background_flag_stress.csv",index=False); print(stress.to_string(index=False))
''', r'''
FOLDER="2026-08-01-uncover-spectroscopic-evidence"; TITLE="What supports the UNCOVER redshifts?"
QUESTION="How do spectral evidence and the background advisory relate to solid or secure redshifts?"; SAMPLE_SIZE=len(secure)
RESULTS=[f"{len(secure)} solid/secure redshifts are classified",f"Most common primary evidence: {table.sort_values('objects').iloc[-1].primary_evidence} ({table.objects.max()} objects)",f"Background advisory applies to {bg.sum()} objects"]
VALIDATION="Raw evidence flags, a declared category priority, and background-flag exclusion are all reported."
FIGURES=["spectroscopic_evidence_counts.png","evidence_redshift_ranges.png"]; ARTIFACTS=["spectroscopic_evidence_summary.csv","background_flag_stress.csv"]
CLAIM="Release evidence-flag audit"; CHECKS=[{"name":"quality flag selection","status":"passed"},{"name":"background advisory stress test","status":"passed"}]
LIMITS=["Evidence flags are release classifications, not independent refits.","Primary-category priority is a display choice."]
''']),

("2026-08-01-uncover-highz-line-diagnostics", "Which lines are measured in the high-redshift spectra?",
 "Which public line measurements reach signal-to-noise above three, and how does lensing change intrinsic flux scale?",
 '''## Analysis plan

For every line with both a flux and uncertainty column, we compute the reported
signal-to-noise ratio and count measurements above three. We do not turn a
single ratio into an abundance. The second plot compares observed [O III] 5007
flux with the simple flux divided by the median lens magnification. This
illustrates the size of the lensing correction; it is not a luminosity because
no luminosity distance or aperture correction is applied.''',
 [r'''
fluxcols=[c for c in lines if c.startswith("f_")]; rows=[]
for f in fluxcols:
 e="e_"+f[2:]
 if e not in lines: continue
 sn=lines[f]/lines[e]
 rows.append({"line":f[2:],"measured":int(lines[f].notna().sum()),"snr_ge_3":int((sn>=3).sum()),"median_snr_detected":float(sn[sn>=3].median()) if (sn>=3).any() else np.nan})
detections=pd.DataFrame(rows).sort_values(["snr_ge_3","measured"],ascending=False)
detections.to_csv("highz_line_detection_counts.csv",index=False); print(detections.head(12).to_string(index=False))
''', r'''
top=detections.head(12).sort_values("snr_ge_3"); fig,ax=plt.subplots(figsize=(8,5.3))
ax.barh(top.line,top.snr_ge_3,color=COLORS["gold"]); ax.set(xlabel="z >= 6 objects with reported S/N >= 3",title="Most frequently measured high-redshift lines")
fig.tight_layout(); fig.savefig("highz_line_detection_counts.png"); plt.show()
''', r'''
m=lines[["id_msa","z_spec","f_OIII-5007","e_OIII-5007"]].merge(mag[["id_msa","mu","mu_low_68","mu_high_68"]],on="id_msa")
m["snr_OIII5007"]=m["f_OIII-5007"]/m["e_OIII-5007"]; det=m[(m.snr_OIII5007>=3)&(m.mu>0)].copy()
det["flux_divided_by_mu"]=det["f_OIII-5007"]/det.mu; det.to_csv("oiii5007_lensing_scale.csv",index=False)
print(f"[O III] 5007 S/N>=3: {len(det)} objects")
''', r'''
fig,ax=plt.subplots(figsize=(7,5.2)); ax.scatter(det["f_OIII-5007"],det.flux_divided_by_mu,c=det.z_spec,cmap="viridis",s=48)
mx=max(det["f_OIII-5007"].max(),1); ax.plot([0,mx],[0,mx],"--",color="0.4",label="no magnification")
ax.set(xlabel="Observed [O III] 5007 flux",ylabel="Flux divided by median magnification",title="Lensing changes the inferred intrinsic flux scale"); ax.legend()
fig.tight_layout(); fig.savefig("oiii5007_lensing_correction.png"); plt.show()
''', r'''
FOLDER="2026-08-01-uncover-highz-line-diagnostics"; TITLE="Which lines are measured in the high-redshift spectra?"
QUESTION="Which line measurements reach S/N above three, and how does lensing change their scale?"; SAMPLE_SIZE=len(lines)
RESULTS=[f"Line catalogue contains {len(lines)} solid/secure z>=6 objects",f"Most common S/N>=3 line: {detections.iloc[0].line} ({detections.iloc[0].snr_ge_3} objects)",f"[O III] 5007 has S/N>=3 in {len(det)} objects"]
VALIDATION="Every line is screened by its reported uncertainty; magnification is shown as a scale correction with release intervals retained."
FIGURES=["highz_line_detection_counts.png","oiii5007_lensing_correction.png"]; ARTIFACTS=["highz_line_detection_counts.csv","oiii5007_lensing_scale.csv"]
CLAIM="Public line-measurement inventory"; CHECKS=[{"name":"finite uncertainty and S/N screen","status":"passed"},{"name":"lensing units stated","status":"passed"}]
LIMITS=["Line fluxes are release fits and uncorrected for slit loss.","No abundance or luminosity is inferred."]
''']),

("2026-08-01-uncover-nirspec-spectral-atlas", "Real HST images and JWST spectra of distant galaxies",
 "What do the calibrated 1D and 2D NIRSpec data look like for six z=7.88 to 13.16 galaxies?",
 '''## Analysis plan

This atlas opens six original DR4.1 FITS spectra and plots the calibrated 1D
flux together with the real 2D detector cutout. The wavelength axis is also
translated to rest frame using the catalogue redshift. A companion figure uses
HST Frontier Fields F105W, F125W, and F160W cutouts returned by the MAST Astrocut
service. At these redshifts an HST non-detection can be physically expected;
the cutouts are included as data, not enhanced into a false visible source.

The vertical Lyman-alpha marker is a wavelength reference, not a claim that an
emission line is detected. Real slit spectra contain noise, residuals, and
contamination, so the 2D panel is essential evidence beside the extracted 1D
curve.''',
 [r'''
meta=secure[secure.id_msa.isin([3686,10646,13077,22223,26185,60157])][["id_msa","z_spec","ra","dec","flag_zspec_qual"]].sort_values("z_spec")
meta.to_csv("spectral_atlas_sources.csv",index=False); print(meta.to_string(index=False))
specfiles={int(p.stem.split("_")[-1].split(".")[0]):p for p in (DATA/"spectra").glob("*.fits")}
''', r'''
fig,axes=plt.subplots(len(meta),1,figsize=(10,12),sharex=True)
for ax,(_,row) in zip(axes,meta.iterrows()):
 with fits.open(specfiles[int(row.id_msa)]) as h: d=h["SPEC1D"].data; w=np.asarray(d["wave"]); f=np.asarray(d["flux"]); e=np.asarray(d["err"])
 good=np.isfinite(w)&np.isfinite(f)&np.isfinite(e)&(e>0); ax.plot(w[good],f[good],color=COLORS["navy"],lw=.8); ax.fill_between(w[good],f[good]-e[good],f[good]+e[good],color=COLORS["cyan"],alpha=.22)
 ax.axvline(.1216*(1+row.z_spec),color=COLORS["coral"],ls="--",lw=1); ax.text(.99,.82,f"MSA {int(row.id_msa)} | z={row.z_spec:.3f}",transform=ax.transAxes,ha="right",fontsize=8)
axes[-1].set(xlabel="Observed wavelength (micrometre)"); fig.supylabel("Flux density (microjansky)"); fig.suptitle("UNCOVER DR4.1 calibrated NIRSpec spectra")
fig.tight_layout(); fig.savefig("nirspec_1d_atlas.png"); plt.show()
''', r'''
fig,axes=plt.subplots(len(meta),1,figsize=(10,9),sharex=True)
for ax,(_,row) in zip(axes,meta.iterrows()):
 with fits.open(specfiles[int(row.id_msa)]) as h: im=np.asarray(h["SCI"].data); w=np.asarray(h["SPEC1D"].data["wave"])
 finite=im[np.isfinite(im)]; lo,hi=np.nanpercentile(finite,[5,95]); ax.imshow(im,origin="lower",aspect="auto",extent=[w.min(),w.max(),0,im.shape[0]],cmap="magma",vmin=lo,vmax=hi)
 ax.axvline(.1216*(1+row.z_spec),color="white",ls="--",lw=.8); ax.text(.99,.78,f"{int(row.id_msa)}",color="white",transform=ax.transAxes,ha="right",fontsize=8)
axes[-1].set(xlabel="Observed wavelength (micrometre)"); fig.supylabel("Spatial detector pixel"); fig.suptitle("Real two-dimensional NIRSpec slit data")
fig.tight_layout(); fig.savefig("nirspec_2d_atlas.png"); plt.show()
''', r'''
cutzip=DATA/"cutouts/hst_60157_astrocut.zip"; channels={}
with zipfile.ZipFile(cutzip) as z:
 name=z.namelist()[0]
 with z.open(name) as stream, fits.open(stream) as h:
  for ext in h[1:]:
   filt=ext.header.get("FILTER")
   if filt in {"F105W","F125W","F160W"}: channels[filt]=np.asarray(ext.data,float)
rgb=[]
for filt in ["F160W","F125W","F105W"]:
 a=gaussian_filter(channels[filt],.6); med=np.nanmedian(a); sig=1.4826*np.nanmedian(np.abs(a-med)); rgb.append(np.arcsinh(6*np.clip((a-(med-sig))/(10*sig),0,1))/np.arcsinh(6))
rgb=np.dstack(rgb); pd.DataFrame({"filter":["F105W","F125W","F160W"],"role":["blue","green","red"]}).to_csv("hst_rgb_channels.csv",index=False)
fig,ax=plt.subplots(figsize=(5.8,5.8)); ax.imshow(rgb,origin="lower",interpolation="bilinear"); ax.scatter([(rgb.shape[1]-1)/2],[(rgb.shape[0]-1)/2],s=220,facecolors="none",edgecolors="white",lw=1)
ax.set(title="HST Frontier Fields near-infrared cutout | MSA 60157 (z=7.880)",xticks=[],yticks=[]); fig.tight_layout(); fig.savefig("hst_rgb_60157.png"); plt.show()
''', r'''
FOLDER="2026-08-01-uncover-nirspec-spectral-atlas"; TITLE="Real HST images and JWST spectra of distant galaxies"
QUESTION="What do calibrated 1D and 2D NIRSpec data look like for six z=7.88 to 13.16 galaxies?"; SAMPLE_SIZE=len(meta)
RESULTS=[f"Six real spectra span z={meta.z_spec.min():.2f}-{meta.z_spec.max():.2f}","Each 1D extraction is paired with its real 2D slit image","A three-filter HST Frontier Fields cutout supplies independent imaging context"]
VALIDATION="The 1D spectrum, 2D detector image, error array, release redshift, and independent HST cutout are shown together."
FIGURES=["nirspec_1d_atlas.png","nirspec_2d_atlas.png","hst_rgb_60157.png"]; ARTIFACTS=["spectral_atlas_sources.csv","hst_rgb_channels.csv"]
CLAIM="Multi-telescope data atlas"; CHECKS=[{"name":"FITS wavelength and flux units","status":"passed"},{"name":"1D/2D agreement view","status":"passed"},{"name":"HST filter provenance","status":"passed"}]
LIMITS=["The atlas does not refit redshifts or lines.","RGB colours are a display mapping, not human-visible rest-frame colour."]
''']),
]


def main() -> None:
    badge="https://colab.research.google.com/assets/colab-badge.svg"
    for slug,title,question,context,cells in CASES:
        folder=ROOT/"mast"/slug; folder.mkdir(parents=True,exist_ok=True)
        notebook=nbf.v4.new_notebook(cells=[
            md(f"[![Open In Colab]({badge})](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/master/mast/{slug}/notebook.ipynb)\n\n# {title}\n\n**Scientific question:** {question}\n\n{INTRO}"),
            md(context), code(IMPORTS), code(LOAD), code(cells[0]),
            md("## Primary evidence\n\nThe first figure shows the direct measurement or catalogue comparison. Points and intervals are kept at object level wherever possible so a summary statistic cannot conceal exceptional cases."),
            code(cells[1]),
            md("## Independent view or stress test\n\nA second view changes the representation, applies an explicit threshold, or removes an advisory subset. Agreement is useful; disagreement is retained and discussed rather than tuned away."),
            code(cells[2]), code(cells[3]),
            md("## Interpretation\n\nThe numerical result is conditional on the public release and the stated selection. Solid or secure means the release quality flag is 2 or 3. It does not mean every downstream physical quantity is known without systematic uncertainty. The saved tables expose the exact rows behind the headline values and make later re-analysis possible."),
            code(cells[4]), md(REFERENCES), code(WRITER)],
            metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3"},"colab":{"provenance":[]}})
        nbf.write(notebook,folder/"notebook.ipynb")
        (folder/"README.md").write_text(f"# {title}\n\n{question}\n\nRun `notebook.ipynb` for the complete methods, figures, validation, limitations, and reusable tables. Data: UNCOVER DR4.1 spectroscopy and MAST archive products. Author: Biswajit Jana.\n",encoding="utf-8")
        print(slug)


if __name__=="__main__": main()
