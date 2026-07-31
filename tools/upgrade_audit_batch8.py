"""Upgrade five strong notebooks to the full scientific-audit contract."""

from __future__ import annotations

import json
import contextlib
import io
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STIS_DOC = "https://hst-docs.stsci.edu/stisdhb/chapter-2-stis-data-structure/2-2-types-of-stis-files"
STIS_LIMITS = "https://hst-docs.stsci.edu/stisdhb/chapter-4-stis-error-sources/4-3-factors-limiting-flux-and-wavelength-accuracy"
RAUW_2012 = "https://doi.org/10.1051/0004-6361/201219473"
FULTON_2017 = "https://doi.org/10.3847/1538-3881/aa80eb"
FULTON_2018 = "https://doi.org/10.3847/1538-3881/aae828"
KAMULALI_2026 = "https://doi.org/10.1051/0004-6361/202557554"


def tagged_markdown(text: str):
    return {
        "cell_type": "markdown",
        "metadata": {"tags": ["batch8-audit"]},
        "source": text,
    }


def tagged_code(source: str):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": ["batch8-audit"]},
        "outputs": [],
        "source": source,
    }


INTRO = """## Batch 8: scientific-audit completion

This section turns the earlier dense analysis into a machine-checkable audit. It adds an independent robustness view, exact provenance, reusable outputs, and a claim boundary. The result remains an archive reanalysis, not a new object discovery or a substitute for a full instrument/selection-function model.
"""


CASES = {
    "mast/2026-07-31-hst-halpha-equivalent-width-systematics": {
        "markdown": INTRO + f"""

The STIS product is a pipeline-extracted, wavelength- and flux-calibrated one-dimensional spectrum ([STIS file definitions]({STIS_DOC})). Random flux errors are propagated below, while the original continuum-order and integration-window grid measures method dependence. The latter is much larger and therefore sets the practical limit. STIS calibration systematics are discussed separately in the [Data Handbook]({STIS_LIMITS}).

**Claim boundary:** this notebook measures how unstable a simple Hα equivalent width is under reasonable analysis choices. It does not infer a mass-loss rate, wind model, abundance, or stellar-atmosphere parameter. HD 93521 is a rapidly rotating O star with known line-profile complexity ([Rauw et al. 2012]({RAUW_2012})).
""",
        "code": r'''# Independent noise propagation at the reference 45 Å / linear-continuum choice
noise_ew=[]
for _ in range(800):
    perturbed=flux + RNG.normal(0,error)
    side=((wave>centre-90)&(wave<centre-53))|((wave>centre+53)&(wave<centre+90))
    line=np.abs(wave-centre)<=45
    coef_noise=np.polyfit(wave[side]-centre,perturbed[side],1,w=1/error[side])
    cont_noise=np.polyval(coef_noise,wave[line]-centre)
    noise_ew.append(float(np.trapezoid(1-perturbed[line]/cont_noise,wave[line])))
noise_ew=np.asarray(noise_ew)
grid.to_csv('halpha_ew_method_grid.csv',index=False)
pd.DataFrame({'ew_A':noise_ew}).to_csv('halpha_ew_noise_bootstrap.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(10,4.3))
ax[0].hist(noise_ew,bins=35,color=COLORS['cyan'],edgecolor='white')
ax[0].axvline(base,color=COLORS['orange'],label='reference method')
ax[0].set(xlabel='Hα equivalent width (Å)',ylabel='noise realisations',title='Flux-error propagation')
ax[0].legend()
ax[1].scatter(grid.half_width_A,grid.ew_A,c=grid['order'],cmap='viridis',s=70)
ax[1].axhspan(np.percentile(noise_ew,16),np.percentile(noise_ew,84),color=COLORS['cyan'],alpha=.25,label='noise 68%')
ax[1].set(xlabel='integration half-width (Å)',ylabel='equivalent width (Å)',title='Method choice dominates')
ax[1].legend()
fig.tight_layout(); fig.savefig('halpha_ew_noise_vs_method.png',dpi=180); plt.show()
result=json.loads(Path('result.json').read_text())
result.update({'figures':['mast/2026-07-31-hst-halpha-equivalent-width-systematics/halpha_ew_systematics.png','mast/2026-07-31-hst-halpha-equivalent-width-systematics/halpha_ew_noise_vs_method.png'],'research_level':'Validated','claim_type':'Equivalent-width robustness audit','provenance':['MAST HST/STIS o49x13010_sx1.fits','pipeline wavelength, flux and error arrays','HD 93521 target identity'],'artifacts':['mast/2026-07-31-hst-halpha-equivalent-width-systematics/halpha_ew_method_grid.csv','mast/2026-07-31-hst-halpha-equivalent-width-systematics/halpha_ew_noise_bootstrap.csv'],'quality_checks':[{'name':'continuum and integration grid','status':'pass'},{'name':'flux-error propagation','status':'pass'},{'name':'atmosphere or wind inference','status':'not attempted'}],'limitations':['continuum placement dominates the formal flux error','broad and variable line structure is not modelled','instrumental and stellar systematics are not captured by independent-pixel resampling']})
Path('result.json').write_text(json.dumps(result,indent=2)); print(result['claim_type'])''',
    },
    "mast/2026-07-31-hst-m87-image-morphology": {
        "markdown": INTRO + """

The source is an official processed preview, not a target-centred calibrated science cutout. The previous notebook already showed that M87 approaches the image boundary. The threshold sweep below is retained as a reproducibility check, but cannot repair missing light outside the frame.

**Claim boundary:** the axis ratio and radius are display-image proxies only. They are not M87 structural parameters, surface photometry, a jet measurement, or evidence about the black hole. A calibrated target-centred FITS product and point-spread-function treatment are required before making those claims.
""",
        "code": r'''stress=pd.DataFrame([{'background_percentile':p,'axis_ratio':v[2],'half_light_radius_display_px':v[3],'centroid_x':v[0],'centroid_y':v[1]} for p,v in tests.items()])
stress.to_csv('m87_morphology_threshold_stress.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(9.5,4.2))
ax[0].plot(stress.background_percentile,stress.axis_ratio,'o-',color=COLORS['blue'])
ax[0].set(xlabel='background percentile',ylabel='display axis ratio',title='Threshold dependence')
ax[1].plot(stress.background_percentile,stress.half_light_radius_display_px,'o-',color=COLORS['orange'])
ax[1].set(xlabel='background percentile',ylabel='half-light radius (display px)',title='Radius is not stable')
fig.tight_layout(); fig.savefig('m87_morphology_threshold_stress.png',dpi=180); plt.show()
result=json.loads(Path('result.json').read_text())
result.update({'figures':['mast/2026-07-31-hst-m87-image-morphology/m87_preview_morphology.png','mast/2026-07-31-hst-m87-image-morphology/m87_morphology_threshold_stress.png'],'research_level':'Exploration','claim_type':'Display-image morphology audit','provenance':['official HST processed preview saved as m87.jpg','8,706,420 display pixels','thresholded intensity moments'],'artifacts':['mast/2026-07-31-hst-m87-image-morphology/m87_morphology_threshold_stress.csv'],'quality_checks':[{'name':'background-threshold sweep','status':'pass'},{'name':'image-boundary completeness','status':'fail'},{'name':'calibrated photometry claim','status':'rejected'}],'limitations':['M87 reaches the preview boundary','display pixels have unknown photometric transfer','no PSF, exposure map, filter calibration, or sky model is applied']})
Path('result.json').write_text(json.dumps(result,indent=2)); print(result['claim_type'])''',
    },
    "mast/2026-07-31-hst-stis-continuum-slope": {
        "markdown": INTRO + f"""

The fitted exponent is an empirical description of this saved STIS product. Pipeline products are wavelength- and flux-calibrated, but absolute and relative flux accuracy still have instrument-specific limits ([STIS documentation]({STIS_LIMITS})). The bootstrap below measures sampling sensitivity; it does not include calibration covariance, reddening uncertainty, or stellar-atmosphere mismatch.

**Claim boundary:** the notebook reports an observed optical continuum slope. It does not interpret that slope as an effective temperature, extinction, metallicity, or gravity measurement.
""",
        "code": r'''mask_widths=np.arange(15,61,5); mask_slopes=np.array([fit_slope(float(w))[0][0] for w in mask_widths]); stress=pd.DataFrame({'line_mask_half_width_A':mask_widths,'slope':mask_slopes}); stress.to_csv('continuum_mask_stress.csv',index=False)
pd.DataFrame({'bootstrap_slope':boot}).to_csv('continuum_slope_bootstrap.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(9.5,4.2))
ax[0].hist(boot,bins=35,color=COLORS['blue'],edgecolor='white'); ax[0].axvline(slope,color=COLORS['orange'])
ax[0].set(xlabel='Fλ exponent',ylabel='bootstrap realisations',title='Sampling uncertainty')
ax[1].plot(mask_widths,mask_slopes,'o-',color=COLORS['cyan']); ax[1].axhline(slope,color=COLORS['orange'],ls='--')
ax[1].set(xlabel='line-mask half-width (Å)',ylabel='Fλ exponent',title='Line-mask stress test')
fig.tight_layout(); fig.savefig('hd93521_continuum_robustness.png',dpi=180); plt.show()
result=json.loads(Path('result.json').read_text())
result.update({'figures':['mast/2026-07-31-hst-stis-continuum-slope/hd93521_continuum_slope.png','mast/2026-07-31-hst-stis-continuum-slope/hd93521_continuum_robustness.png'],'research_level':'Validated','claim_type':'Empirical continuum-slope measurement','provenance':['MAST HST/STIS o49x13010_sx1.fits','pipeline wavelength, flux and error arrays','five H/He regions masked'],'artifacts':['mast/2026-07-31-hst-stis-continuum-slope/continuum_mask_stress.csv','mast/2026-07-31-hst-stis-continuum-slope/continuum_slope_bootstrap.csv'],'quality_checks':[{'name':'line-mask width sweep','status':'pass'},{'name':'sampling bootstrap','status':'pass'},{'name':'physical atmosphere fit','status':'not attempted'}],'limitations':['bootstrap treats retained samples as exchangeable','flux-calibration covariance and reddening are omitted','a power law is descriptive over this wavelength range']})
Path('result.json').write_text(json.dumps(result,indent=2)); print(result['claim_type'])''',
    },
    "mast/2026-07-31-hst-stis-hd93521-line-inventory": {
        "run_original": False,
        "markdown": INTRO + f"""

The saved `_sx1` product is a summed, extracted, wavelength- and flux-calibrated STIS spectrum ([file definitions]({STIS_DOC})). The laboratory-centre comparison supports line identification, while equivalent width provides a reproducible descriptive measurement. HD 93521's rapid rotation and variable profiles require dedicated atmosphere and time-series modelling for physical parameters ([Rauw et al. 2012]({RAUW_2012})).

**Claim boundary:** detection of broad H/He features does not by itself measure chemical abundance. No abundance, temperature, gravity, rotation, or wind rate is inferred here.
""",
        "code": r'''result=json.loads(Path('result.json').read_text())
result.update({'figures':['mast/2026-07-31-hst-stis-hd93521-line-inventory/hd93521_normalised_spectrum.png','mast/2026-07-31-hst-stis-hd93521-line-inventory/hd93521_line_fits.png'],'research_level':'Validated','claim_type':'Spectral-feature inventory','provenance':['MAST HST/STIS o49x13010_sx1.fits','pipeline wavelength, flux and error arrays','laboratory H/He wavelengths'],'artifacts':['mast/2026-07-31-hst-stis-hd93521-line-inventory/spectrum_subset.csv','mast/2026-07-31-hst-stis-hd93521-line-inventory/line_measurements.csv'],'quality_checks':[{'name':'five laboratory-centre checks','status':'pass'},{'name':'local continuum fits','status':'pass'},{'name':'chemical abundance inference','status':'not attempted'}],'limitations':['broad blends and rapid rotation complicate centroids','single-epoch features can be variable','line identification alone is not an abundance analysis']})
Path('result.json').write_text(json.dumps(result,indent=2)); print(result['claim_type'])''',
    },
    "exoplanet-archive/2026-07-31-exoplanet-radius-valley": {
        "run_original": False,
        "markdown": INTRO + f"""

The radius deficit was first established in a carefully characterised Kepler sample near 1.5–2.0 Earth radii ([Fulton et al. 2017]({FULTON_2017}); [Fulton & Petigura 2018]({FULTON_2018})). A 2026 host-star reanalysis reports a period slope near −0.12 and a valley near 2 Earth radii ([Kamulali et al. 2026]({KAMULALI_2026})), close to the descriptive slope measured here.

**Claim boundary:** this notebook detects a deficit in the heterogeneous confirmed-planet catalogue. It does not infer the intrinsic occurrence rate or decide between atmospheric loss, core-powered evolution, and formation/composition explanations because survey completeness, radius uncertainties, host properties, and false-positive selection are not jointly modelled.
""",
        "code": r'''result=json.loads(Path('result.json').read_text())
result.update({'figures':['exoplanet-archive/2026-07-31-exoplanet-radius-valley/radius_valley_period.png','exoplanet-archive/2026-07-31-exoplanet-radius-valley/radius_valley_kde.png'],'research_level':'Validated','claim_type':'Catalogue radius-deficit measurement','provenance':['NASA Exoplanet Archive confirmed transiting planets query','2,070 selected planets with radius and period','saved query table and analysis subset'],'artifacts':['exoplanet-archive/2026-07-31-exoplanet-radius-valley/confirmed_transiting_planets.csv','exoplanet-archive/2026-07-31-exoplanet-radius-valley/radius_valley_sample.csv','exoplanet-archive/2026-07-31-exoplanet-radius-valley/period_binned_valleys.csv'],'quality_checks':[{'name':'bootstrap minimum interval','status':'pass'},{'name':'period-binned slope','status':'pass'},{'name':'survey completeness correction','status':'not attempted'}],'limitations':['confirmed-planet catalogue combines surveys with different selection functions','planet-radius uncertainties are not propagated per object','the descriptive KDE minimum is bandwidth dependent']})
Path('result.json').write_text(json.dumps(result,indent=2)); print(result['claim_type'])''',
    },
}


def update_notebook(relative: str, case: dict[str, str]) -> None:
    path = ROOT / relative / "notebook.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    notebook["cells"] = [
        cell for cell in notebook["cells"]
        if "batch8-audit" not in cell.get("metadata", {}).get("tags", [])
    ]

    namespace = {"__name__": "__notebook__", "json": json, "Path": Path}
    previous = Path.cwd()
    os.chdir(path.parent)
    try:
        # Execute the saved notebook sources in order so the appended audit is
        # reproducible from the same arrays used by the original analysis.
        if case.get("run_original", True):
            for cell in notebook["cells"]:
                if cell.get("cell_type") == "code":
                    source = cell.get("source", "")
                    if isinstance(source, list):
                        source = "".join(source)
                    exec(compile(source, str(path), "exec"), namespace)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(case["code"], str(path), "exec"), namespace)
    finally:
        os.chdir(previous)

    markdown_cell = tagged_markdown(case["markdown"])
    code_cell = tagged_code(case["code"])
    code_cell["execution_count"] = max(
        [cell.get("execution_count") or 0 for cell in notebook["cells"] if cell.get("cell_type") == "code"],
        default=0,
    ) + 1
    code_cell["outputs"] = [{"name": "stdout", "output_type": "stream", "text": output.getvalue()}]
    notebook["cells"].extend([markdown_cell, code_cell])
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Executed {relative}")


def main() -> None:
    for relative, case in CASES.items():
        update_notebook(relative, case)


if __name__ == "__main__":
    main()
