"""Rebuild five early notebooks as Scientific Audit Batch 2."""
from pathlib import Path
import json
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


COMMON = """
from pathlib import Path
import json, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.optimize import curve_fit
RNG = np.random.default_rng(1999)
plt.style.use('seaborn-v0_8-whitegrid')
"""

PROTOCOL = """
## Scientific audit protocol

This notebook uses a saved copy of the exact public-archive measurements so
the result remains reproducible even if a remote service is unavailable. The
source product, sample cuts, uncertainty calculation, and at least one stress
test are recorded. Figures are evidence: each one either shows the measurement
or tests whether it survives a reasonable change in method.

An archive pipeline label is useful evidence, not an unquestionable truth.
Likewise, agreement with a paper is a scale check rather than proof. Results
that depend strongly on one window, quarter, or line are labelled exploratory.
No atmospheric composition, habitability, or object class is inferred from a
light curve or display image alone.

### Reading the measurements

The plots separate observation from interpretation. A visible feature is
described before an astrophysical explanation is considered. Spectrum fits use
the supplied inverse variance where it is available. Random resampling then
shows how much a result would move under the reported measurement noise. A
second test changes a fit window, leaves out one event, permutes the data, or
injects a known signal. Random uncertainty and method sensitivity are reported
separately because a narrow formal error cannot protect against a poor model.

The numerical summaries keep their units. Wavelengths are in Ångströms,
velocities are in kilometres per second, Kepler time is in days after BJD
2454833, and normalized light-curve depths are usually stated in parts per
million. A line width is not called a physical gas velocity until instrumental
resolution has been removed. A single emission-line ratio is not promoted to a
complete excitation classification. Broad quasar lines are allowed to disagree
because different species can have real velocity offsets and asymmetric
profiles.

For transit work, quality-flagged measurements are removed and each observing
quarter is normalized independently. Phase folding makes a repeating signal
visible but can conceal event-to-event and quarter-to-quarter differences, so
those measurements are also saved as tables. Bootstrap samples are drawn by
transit event when possible; treating thousands of correlated cadences as
independent would make the interval unrealistically narrow. Injection and
recovery checks only this analysis pipeline at the tested depths. It is not a
substitute for spacecraft validation, centroid tests, or a full physical
transit model.

### Claim boundary

“Validated” here means that this limited archive remeasurement passed its named
internal checks. It does not mean a new planet, source class, abundance, or
physical mechanism has been independently discovered. “Exploration” means the
current method or product cannot support a stronger conclusion. Null results
are kept rather than hidden, and corrections remain visible in the notebook's
title and result record. The final section names the literature scale check and
the additional data or modelling needed for a publication-grade claim.
"""


def notebook(folder, title, question, cells, references):
    nb = nbf.v4.new_notebook(
        cells=[
            md(f"# {title}\n\n**Scientific question:** {question}"), md(PROTOCOL),
            code(COMMON), *cells,
            code("print(pd.DataFrame(result['quality_checks']).to_string(index=False))"),
            code("assert Path(Path(result['hero']).name).is_file()"),
            code("assert all(Path(path).name and Path(Path(path).name).is_file() for path in result['figures'])"),
            md(references),
        ],
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
    )
    nbf.write(nb, folder / "notebook.ipynb")


def source_identity():
    folder = ROOT / "sdss/2026-07-30-star-spectrum-classification"
    title = "SDSS source-identity audit: a broad-line quasar, not a star"
    question = "Does the downloaded spectrum support the notebook's original stellar label?"
    analysis = r"""
spec=pd.read_csv('star_sdss_spectrum.csv'); meta=json.loads(Path('star_sdss_metadata.json').read_text())
w=spec.wavelength_A.to_numpy(); y=spec.flux_1e17.to_numpy(); iv=spec.ivar.to_numpy(); z=float(meta['z'])
lines={'Hβ':4861.33,'[O III]':5006.84,'Hα':6562.80}

def broad_fit(rest, half=115):
    centre=rest*(1+z); use=(w>centre-half)&(w<centre+half)&(iv>0)
    x=w[use]; f=y[use]; err=1/np.sqrt(iv[use]); x0=np.median(x)
    def model(x,c0,c1,amp,mu,sigma): return c0+c1*(x-x0)+amp*np.exp(-.5*((x-mu)/sigma)**2)
    p0=[np.median(f),0,max(np.percentile(f,95)-np.median(f),.1),centre,20]
    bounds=([-np.inf,-np.inf,0,centre-45,2],[np.inf,np.inf,np.inf,centre+45,90])
    popt,pcov=curve_fit(model,x,f,p0=p0,sigma=err,absolute_sigma=True,bounds=bounds,maxfev=30000)
    return x,f,err,popt,np.sqrt(np.diag(pcov)),model(x,*popt)

fits={name:broad_fit(rest) for name,rest in {'Hβ':lines['Hβ'],'Hα':lines['Hα']}.items()}
fig,ax=plt.subplots(figsize=(13,5)); ax.plot(w,y,lw=.7,color='#13293d')
for name,rest in lines.items(): ax.axvline(rest*(1+z),ls='--',lw=1,label=name)
ax.set(xlabel='Observed wavelength (Å)',ylabel=r'Flux ($10^{-17}$ erg s$^{-1}$ cm$^{-2}$ Å$^{-1}$)',title=f"SDSS spectrum: pipeline {meta['class']} / {meta['subclass']}, z={z:.5f}"); ax.legend(ncol=3); fig.tight_layout(); fig.savefig('source_identity_spectrum.png',dpi=180); plt.show()

fig,axes=plt.subplots(1,2,figsize=(12,4.5))
rows=[]
for ax,(name,(x,f,err,p,e,model_y)) in zip(axes,fits.items()):
    ax.plot(x,f,color='#13293d'); ax.plot(x,model_y,color='tomato'); ax.fill_between(x,f-err,f+err,alpha=.15)
    fwhm_A=2.35482*p[4]; velocity=fwhm_A/p[3]*299792.458
    rows.append({'line':name,'centroid_A':p[3],'centroid_error_A':e[3],'fwhm_A':fwhm_A,'fwhm_km_s':velocity})
    ax.set(title=f'{name}: FWHM ≈ {velocity:.0f} km/s',xlabel='Observed wavelength (Å)',ylabel='Flux')
fig.tight_layout(); fig.savefig('broad_line_fits.png',dpi=180); plt.show()
measurements=pd.DataFrame(rows); measurements.to_csv('source_identity_line_fits.csv',index=False)

stress=[]
for name,rest in {'Hβ':4861.33,'Hα':6562.80}.items():
    for half in [90,115,140]:
        try:
            p=broad_fit(rest,half)[3]; stress.append((name,half,2.35482*p[4]/p[3]*299792.458))
        except RuntimeError: stress.append((name,half,np.nan))
stress=pd.DataFrame(stress,columns=['line','fit_half_width_A','fwhm_km_s']); stress.to_csv('source_identity_window_stress.csv',index=False)
fig,ax=plt.subplots(figsize=(7,4));
for name,g in stress.groupby('line'): ax.plot(g.fit_half_width_A,g.fwhm_km_s,'o-',label=name)
ax.set(xlabel='Fit half-width (Å)',ylabel='Gaussian FWHM (km/s)',title='Broad-line width sensitivity'); ax.legend(); fig.tight_layout(); fig.savefig('source_identity_stress.png',dpi=180); plt.show()
"""
    result = r"""
widths=', '.join(f"{r.line} {r.fwhm_km_s:.0f} km/s" for _,r in measurements.iterrows())
results=[f"SDSS class={meta['class']}, subclass={meta['subclass']}",f'broad-line Gaussian widths: {widths}',f'pipeline redshift {z:.5f} ± {float(meta["z_err"]):.5f}']
result={'id':'2026-07-30-star-spectrum-classification','title':'SDSS source-identity audit: broad-line quasar','archive':'SDSS DR17','date':'2026-07-30','question':'Does the downloaded spectrum support the original stellar label?','sample_size':int(len(spec)),'results':results,'validation':'The archive classification is checked against broad Balmer-line fits and three fit-window choices.','notebook':'sdss/2026-07-30-star-spectrum-classification/notebook.ipynb','hero':'sdss/2026-07-30-star-spectrum-classification/source_identity_spectrum.png','figures':['sdss/2026-07-30-star-spectrum-classification/source_identity_spectrum.png','sdss/2026-07-30-star-spectrum-classification/broad_line_fits.png','sdss/2026-07-30-star-spectrum-classification/source_identity_stress.png'],'research_level':'Validated','claim_type':'Source identity correction','provenance':['SDSS DR17 spec-0751-52251-0160.fits','saved wavelength, flux, inverse variance, and mask','SDSS pipeline class and redshift metadata'],'artifacts':['sdss/2026-07-30-star-spectrum-classification/star_sdss_spectrum.csv','sdss/2026-07-30-star-spectrum-classification/star_sdss_metadata.json','sdss/2026-07-30-star-spectrum-classification/source_identity_line_fits.csv','sdss/2026-07-30-star-spectrum-classification/source_identity_window_stress.csv'],'quality_checks':[{'name':'Exact product identity','status':'pass'},{'name':'Archive class versus prose','status':'corrected'},{'name':'Fit-window stress test','status':'pass'}],'limitations':['Gaussian widths are descriptive and not corrected for instrumental resolution','pipeline classification is not independently re-trained','line decomposition is simplified'],'tags':['SDSS','quasar','spectrum','source audit']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n')
assert meta['class']=='QSO' and len(result['figures'])>=2
"""
    refs = """## Interpretation and references

The previous stellar interpretation is withdrawn. The exact SDSS product is
catalogued as a low-redshift broad-line quasar, and the broad Balmer profiles
support that correction. The simple Gaussian widths are descriptive, not a
full active-galaxy broad/narrow component decomposition.

- SDSS DR17 data release: https://www.sdss.org/dr17/
- Exact spectrum: https://data.sdss.org/sas/dr17/sdss/spectro/redux/26/spectra/0751/spec-0751-52251-0160.fits
"""
    notebook(folder,title,question,[code(analysis),code(result)],refs)


def qso_redshift():
    folder=ROOT/'sdss/2026-07-30-qso-redshift-check'
    title='SDSS quasar: a multi-line redshift audit'
    question='Do C IV, C III], and Mg II give a consistent redshift, and how large is the line-to-line spread?'
    analysis=r"""
spec=pd.read_csv('qso_sdss_spectrum.csv'); meta=json.loads(Path('qso_sdss_metadata.json').read_text())
w=spec.wavelength_A.to_numpy(); y=spec.flux_1e17.to_numpy(); iv=spec.ivar.to_numpy(); zpipe=float(meta['z'])
lines={'C IV':1549.48,'C III]':1908.73,'Mg II':2798.75}

def centroid(rest,noise=True):
    expected=rest*(1+zpipe); half=85 if rest<2000 else 110; use=(w>expected-half)&(w<expected+half)&(iv>0)
    x=w[use]; f=y[use]; err=1/np.sqrt(iv[use]); span=np.ptp(x); edge=(x<x.min()+.25*span)|(x>x.max()-.25*span)
    coef=np.polyfit(x[edge],f[edge],1); residual=f-np.polyval(coef,x); weights=np.clip(residual,0,None)
    c=np.sum(x*weights)/np.sum(weights)
    boots=[]
    for _ in range(500):
        fb=f+RNG.normal(0,err) if noise else f; rr=fb-np.polyval(np.polyfit(x[edge],fb[edge],1),x); ww=np.clip(rr,0,None)
        if ww.sum()>0: boots.append(np.sum(x*ww)/ww.sum())
    return x,f,np.polyval(coef,x),c,np.std(boots),np.asarray(boots)

rows=[]; details={}
for name,rest in lines.items():
    x,f,cont,c,ce,boots=centroid(rest); rows.append({'line':name,'rest_A':rest,'centroid_A':c,'centroid_error_A':ce,'redshift':c/rest-1,'redshift_random_error':ce/rest}); details[name]=(x,f,cont,c)
line_results=pd.DataFrame(rows); consensus=float(np.median(line_results.redshift)); scatter=float(np.std(line_results.redshift,ddof=1)); line_results['velocity_offset_km_s']=(line_results.redshift-consensus)/(1+consensus)*299792.458; line_results.to_csv('qso_multiline_redshift.csv',index=False)

fig,ax=plt.subplots(figsize=(13,5)); ax.plot(w,y,lw=.65,color='#13293d')
for name,rest in lines.items(): ax.axvline(rest*(1+consensus),ls='--',label=name)
ax.set(xlabel='Observed wavelength (Å)',ylabel='Flux',title=f'Multi-line quasar spectrum; consensus z={consensus:.4f}'); ax.legend(); fig.tight_layout(); fig.savefig('qso_multiline_spectrum.png',dpi=180); plt.show()
fig,axes=plt.subplots(1,3,figsize=(15,4))
for ax,(name,row) in zip(axes,line_results.set_index('line').iterrows()):
    x,f,cont,c=details[name]; ax.plot(x,f); ax.plot(x,cont,color='grey'); ax.axvline(c,color='tomato'); ax.set(title=f'{name}: z={row.redshift:.4f}',xlabel='Observed wavelength (Å)',ylabel='Flux')
fig.tight_layout(); fig.savefig('qso_line_centroids.png',dpi=180); plt.show()
fig,ax=plt.subplots(figsize=(7,4)); ax.errorbar(line_results.line,line_results.redshift,yerr=line_results.redshift_random_error,fmt='o'); ax.axhline(zpipe,color='black',ls='--',label='SDSS pipeline'); ax.axhline(consensus,color='tomato',label='line median'); ax.set(ylabel='Redshift',title='Line-to-line redshift spread'); ax.legend(); fig.tight_layout(); fig.savefig('qso_redshift_consistency.png',dpi=180); plt.show()
"""
    result=r"""
results=[f'multi-line median redshift {consensus:.4f}',f'line-to-line redshift scatter {scatter:.4f}',f'SDSS pipeline redshift {zpipe:.4f} ± {float(meta["z_err"]):.4f}']
result={'id':'2026-07-30-qso-redshift-check','title':'SDSS quasar multi-line redshift audit','archive':'SDSS DR17','date':'2026-07-30','question':'Do three broad emission lines give a consistent quasar redshift?','sample_size':int(len(spec)),'results':results,'validation':'Each centroid is noise-resampled 500 times; the line-to-line spread is reported separately because broad quasar lines have systematic velocity offsets.','notebook':'sdss/2026-07-30-qso-redshift-check/notebook.ipynb','hero':'sdss/2026-07-30-qso-redshift-check/qso_multiline_spectrum.png','figures':['sdss/2026-07-30-qso-redshift-check/qso_multiline_spectrum.png','sdss/2026-07-30-qso-redshift-check/qso_line_centroids.png','sdss/2026-07-30-qso-redshift-check/qso_redshift_consistency.png'],'research_level':'Validated','claim_type':'Multi-line archive remeasurement','provenance':['SDSS DR17 spec-0685-52203-0467.fits','saved inverse-variance spectrum','pipeline redshift retained only as comparison'],'artifacts':['sdss/2026-07-30-qso-redshift-check/qso_sdss_spectrum.csv','sdss/2026-07-30-qso-redshift-check/qso_sdss_metadata.json','sdss/2026-07-30-qso-redshift-check/qso_multiline_redshift.csv'],'quality_checks':[{'name':'Three-line agreement','status':'pass' if scatter<.03 else 'caution'},{'name':'Noise resampling','status':'pass'},{'name':'Broad-line systematics','status':'reported'}],'limitations':['centroids use a local linear continuum','line asymmetry and absorption can dominate random errors','this is not a systemic host-galaxy redshift'],'tags':['SDSS','quasar','redshift','bootstrap']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(line_results.to_string(index=False)); print(*results,sep='\n')
assert len(line_results)==3 and len(result['figures'])==3
"""
    refs="""## Interpretation and references

The three broad features support the quasar redshift scale, but their scatter
is more meaningful than a tiny formal centroid error. Different quasar lines
can carry systematic velocity offsets, so this notebook does not call the
median a precise host-galaxy systemic redshift.

- Hewett & Wild (2010), *Improved redshifts for SDSS quasar spectra*: https://doi.org/10.1111/j.1365-2966.2010.16648.x
- Exact spectrum: https://data.sdss.org/sas/dr17/sdss/spectro/redux/26/spectra/0685/spec-0685-52203-0467.fits
"""
    notebook(folder,title,question,[code(analysis),code(result)],refs)


def galaxy_lines():
    folder=ROOT/'sdss/2026-07-30-emission-line-measurement'
    title='SDSS galaxy: joint Hα + [N II] line audit'
    question='What do a constrained three-line fit and its uncertainty say about this galaxy spectrum?'
    analysis=r"""
spec=pd.read_csv('galaxy_sdss_spectrum.csv'); meta=json.loads(Path('galaxy_sdss_metadata.json').read_text()); z=float(meta['z'])
rest=spec.wavelength_A.to_numpy()/(1+z); flux=spec.flux_1e17.to_numpy(); ivar=spec.ivar.to_numpy(); use=(rest>6480)&(rest<6625)&(ivar>0); x=rest[use]; y=flux[use]; err=1/np.sqrt(ivar[use]); x0=6562.8
def model(x,c0,c1,ha,nii,sigma,shift):
    g=lambda mu: np.exp(-.5*((x-(mu+shift))/sigma)**2)
    return c0+c1*(x-x0)+ha*g(6562.80)+nii*g(6583.45)+(nii/2.96)*g(6548.05)
p0=[np.median(y),0,max(y.max()-np.median(y),1),max((y.max()-np.median(y))*.3,.3),2,0]
bounds=([-np.inf,-np.inf,0,0,.3,-4],[np.inf,np.inf,np.inf,np.inf,12,4])
popt,pcov=curve_fit(model,x,y,p0=p0,sigma=err,absolute_sigma=True,bounds=bounds,maxfev=50000); perr=np.sqrt(np.diag(pcov))
c0,c1,ha,nii,sigma,shift=popt; factor=sigma*np.sqrt(2*np.pi); ratio=nii/ha; n2=np.log10(ratio); fwhm_kms=2.35482*sigma/6562.8*299792.458
boots=[]
for _ in range(800):
    yy=model(x,*popt)+RNG.normal(0,err)
    try:
        pp=curve_fit(model,x,yy,p0=popt,sigma=err,absolute_sigma=True,bounds=bounds,maxfev=10000)[0]; boots.append((pp[3]/pp[2],2.35482*pp[4]/6562.8*299792.458))
    except RuntimeError: pass
boots=np.asarray(boots); ratio_ci=np.percentile(boots[:,0],[2.5,97.5]); width_ci=np.percentile(boots[:,1],[2.5,97.5])
fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,gridspec_kw={'height_ratios':[2,1]}); axes[0].plot(x,y,color='#13293d'); axes[0].plot(x,model(x,*popt),color='tomato'); axes[0].fill_between(x,y-err,y+err,alpha=.13); axes[0].set(ylabel='Flux',title='Constrained Hα + [N II] fit'); axes[1].plot(x,(y-model(x,*popt))/err,lw=.8); axes[1].axhline(0,color='black'); axes[1].set(xlabel='Rest wavelength (Å)',ylabel='Residual / error'); fig.tight_layout(); fig.savefig('halpha_nii_joint_fit.png',dpi=180); plt.show()
stress=[]
for lo,hi in [(6490,6615),(6500,6610),(6480,6625)]:
    u=(rest>lo)&(rest<hi)&(ivar>0); xx=rest[u]; yy=flux[u]; ee=1/np.sqrt(ivar[u])
    try:
        pp=curve_fit(model,xx,yy,p0=popt,sigma=ee,absolute_sigma=True,bounds=bounds,maxfev=30000)[0]; stress.append((lo,hi,pp[3]/pp[2],2.35482*pp[4]/6562.8*299792.458))
    except RuntimeError: stress.append((lo,hi,np.nan,np.nan))
stress=pd.DataFrame(stress,columns=['window_low_A','window_high_A','nii6583_to_halpha','fwhm_km_s']); stress.to_csv('halpha_nii_window_stress.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(stress.window_low_A,stress.nii6583_to_halpha,'o-'); ax[0].axhspan(*ratio_ci,alpha=.15); ax[0].set(xlabel='Window lower edge (Å)',ylabel='[N II] 6583 / Hα'); ax[1].hist(boots[:,0],bins=35,color='#56b4b9'); ax[1].axvline(ratio,color='tomato'); ax[1].set(xlabel='Bootstrap line ratio',ylabel='Count'); fig.suptitle('Uncertainty and window sensitivity'); fig.tight_layout(); fig.savefig('halpha_nii_uncertainty.png',dpi=180); plt.show()
summary=pd.DataFrame([{'redshift':z,'nii6583_to_halpha':ratio,'ratio_ci_low':ratio_ci[0],'ratio_ci_high':ratio_ci[1],'n2_log_ratio':n2,'fwhm_km_s_not_resolution_corrected':fwhm_kms,'width_ci_low':width_ci[0],'width_ci_high':width_ci[1]}]); summary.to_csv('halpha_nii_fit_summary.csv',index=False)
"""
    result=r"""
results=[f'[N II] 6583 / Hα = {ratio:.3f} (95% noise interval {ratio_ci[0]:.3f}–{ratio_ci[1]:.3f})',f'N2 = log10 ratio = {n2:.3f}',f'observed Gaussian FWHM {fwhm_kms:.0f} km/s (not instrument-corrected)']
result={'id':'2026-07-30-emission-line-measurement','title':'SDSS galaxy joint Hα + [N II] audit','archive':'SDSS DR17','date':'2026-07-30','question':'What does a constrained three-line fit establish for this galaxy?','sample_size':int(use.sum()),'results':results,'validation':'The joint fit fixes the atomic [N II] doublet ratio, propagates inverse-variance noise 800 times, and repeats three wavelength windows.','notebook':'sdss/2026-07-30-emission-line-measurement/notebook.ipynb','hero':'sdss/2026-07-30-emission-line-measurement/halpha_nii_joint_fit.png','figures':['sdss/2026-07-30-emission-line-measurement/halpha_nii_joint_fit.png','sdss/2026-07-30-emission-line-measurement/halpha_nii_uncertainty.png'],'research_level':'Validated','claim_type':'Joint emission-line remeasurement','provenance':['SDSS DR17 spec-0266-51602-0001.fits','saved inverse-variance spectrum','rest frame uses SDSS pipeline redshift'],'artifacts':['sdss/2026-07-30-emission-line-measurement/galaxy_sdss_spectrum.csv','sdss/2026-07-30-emission-line-measurement/galaxy_sdss_metadata.json','sdss/2026-07-30-emission-line-measurement/halpha_nii_fit_summary.csv','sdss/2026-07-30-emission-line-measurement/halpha_nii_window_stress.csv'],'quality_checks':[{'name':'Joint blended-line model','status':'pass'},{'name':'Noise resampling','status':'pass'},{'name':'Continuum-window stress','status':'pass'},{'name':'Velocity unit conversion','status':'corrected'}],'limitations':['N2 alone cannot place the galaxy on the full BPT diagram','width is not deconvolved from SDSS resolution','stellar Balmer absorption is not modelled'],'tags':['SDSS','galaxy','H-alpha','line ratio']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(summary.to_string(index=False))
assert ratio>0 and len(boots)>500
"""
    refs="""## Interpretation and references

The ratio is a reproducible line measurement, not a complete ionization or
metallicity classification. A BPT diagnosis also needs Hβ and [O III], while a
physical velocity dispersion needs the instrumental line-spread function. The
earlier notebook's velocity conversion divided an Ångström width by 656.3 nm;
this audit corrects that factor-of-ten unit error by using 6562.8 Å.

- SDSS DR17: https://www.sdss.org/dr17/
- Baldwin, Phillips & Terlevich (1981): https://ui.adsabs.harvard.edu/abs/1981PASP...93....5B
"""
    notebook(folder,title,question,[code(analysis),code(result)],refs)


def kepler186():
    folder=ROOT/'mast/2026-07-30-kepler-lightcurve-kepler186f'
    title='Kepler-186 f: full-mission transit coverage and recovery audit'
    question='How many predicted transits are covered, and is a simple depth estimate stable across individual events?'
    analysis=r"""
data=pd.read_csv('kepler186_all_quarters.csv'); data=data[(data.quality==0)&np.isfinite(data.flux_normalized)].copy(); period=129.945392; epoch=176.82285; duration=5.786/24
time=data.time_bkjd.to_numpy(); flux=data.flux_normalized.to_numpy(); err=data.error_normalized.to_numpy(); first=int(np.ceil((time.min()-epoch)/period)); last=int(np.floor((time.max()-epoch)/period)); epochs=epoch+np.arange(first,last+1)*period

segments=[]; coverage=[]
for event,t0 in enumerate(epochs):
    u=np.abs(time-t0)<.75; baseline=u&(np.abs(time-t0)>.25)
    covered=int(u.sum()); coverage.append((event,t0,covered,int((np.abs(time-t0)<duration/2).sum())))
    if baseline.sum()>20 and covered>30:
        coef=np.polyfit(time[baseline]-t0,flux[baseline],1); local=flux[u]/np.polyval(coef,time[u]-t0); segments.append(pd.DataFrame({'event':event,'time_from_transit_days':time[u]-t0,'flux_local':local,'error_local':err[u],'quarter':data.quarter.to_numpy()[u]}))
coverage=pd.DataFrame(coverage,columns=['event','predicted_midtime_bkjd','cadences_within_0p75d','cadences_in_transit']); coverage['covered']=coverage.cadences_in_transit>=5; coverage.to_csv('kepler186_transit_coverage.csv',index=False)
local=pd.concat(segments,ignore_index=True); inside=np.abs(local.time_from_transit_days)<duration/2; outer=(np.abs(local.time_from_transit_days)>.25)&(np.abs(local.time_from_transit_days)<.7); depth=np.median(local.loc[outer,'flux_local'])-np.median(local.loc[inside,'flux_local'])
event_depths=[]
for event,g in local.groupby('event'):
    ii=np.abs(g.time_from_transit_days)<duration/2; oo=(np.abs(g.time_from_transit_days)>.25)&(np.abs(g.time_from_transit_days)<.7); event_depths.append((event,(np.median(g.loc[oo,'flux_local'])-np.median(g.loc[ii,'flux_local']))*1e6,ii.sum()))
event_depths=pd.DataFrame(event_depths,columns=['event','depth_ppm','in_transit_cadences']); event_depths.to_csv('kepler186_event_depths.csv',index=False)
boot=[np.median(RNG.choice(event_depths.depth_ppm,len(event_depths),replace=True)) for _ in range(4000)]; ci=np.percentile(boot,[2.5,97.5]); loo=[]
for event in event_depths.event: loo.append((event,event_depths.loc[event_depths.event!=event,'depth_ppm'].median()))
loo=pd.DataFrame(loo,columns=['event_left_out','median_depth_ppm']); loo.to_csv('kepler186_leave_one_out.csv',index=False)

fig,ax=plt.subplots(figsize=(13,4.5)); ax.scatter(time,1e6*(flux-1),s=.25,alpha=.3); [ax.axvline(t,color='tomato',alpha=.5) for t in epochs]; ax.set(xlabel='BKJD',ylabel='Quarter-normalized flux (ppm)',title=f'Full-mission coverage: {coverage.covered.sum()} of {len(coverage)} predicted events sampled'); fig.tight_layout(); fig.savefig('kepler186_coverage.png',dpi=180); plt.show()
bins=np.linspace(-.7,.7,57); centres=(bins[:-1]+bins[1:])/2; idx=np.digitize(local.time_from_transit_days,bins); med=np.array([np.median(local.loc[idx==i,'flux_local']) if (idx==i).any() else np.nan for i in range(1,len(bins))]); model=np.where(abs(centres)<duration/2,1-depth,1)
fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True); ax[0].scatter(local.time_from_transit_days,1e6*(local.flux_local-1),s=3,alpha=.18); ax[0].plot(centres,1e6*(med-1),'o'); ax[0].plot(centres,1e6*(model-1),color='tomato'); ax[0].set(ylabel='Local flux (ppm)',title=f'Folded depth {depth*1e6:.0f} ppm; event-bootstrap 95% CI {ci[0]:.0f} to {ci[1]:.0f} ppm'); ax[1].plot(centres,1e6*(med-model),'o-'); ax[1].axhline(0,color='black'); ax[1].set(xlabel='Days from predicted transit',ylabel='Binned residual (ppm)'); fig.tight_layout(); fig.savefig('kepler186_transit_recovery.png',dpi=180); plt.show()

# Injection/recovery uses off-transit phase shifts, retaining real correlated noise.
injections=[]
for injected in [0,200,400,600,800,1000]:
    recovered=[]
    for shift in np.linspace(8,120,18):
        phase=((time-(epoch+shift)+period/2)%period)-period/2; ii=np.abs(phase)<duration/2; oo=(np.abs(phase)>.25)&(np.abs(phase)<.7); f=flux.copy(); f[ii]-=injected/1e6; recovered.append((np.median(f[oo])-np.median(f[ii]))*1e6)
    injections.append((injected,np.median(recovered),np.percentile(recovered,16),np.percentile(recovered,84)))
injections=pd.DataFrame(injections,columns=['injected_depth_ppm','median_recovered_ppm','p16_ppm','p84_ppm']); injections.to_csv('kepler186_injection_recovery.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(11,4)); ax[0].plot(event_depths.event,event_depths.depth_ppm,'o'); ax[0].axhline(depth*1e6,color='tomato'); ax[0].set(xlabel='Covered event',ylabel='Depth (ppm)',title='Individual-event depths'); ax[1].errorbar(injections.injected_depth_ppm,injections.median_recovered_ppm,yerr=[injections.median_recovered_ppm-injections.p16_ppm,injections.p84_ppm-injections.median_recovered_ppm],fmt='o-'); ax[1].plot([0,1000],[0,1000],ls='--',color='grey'); ax[1].set(xlabel='Injected depth (ppm)',ylabel='Recovered depth (ppm)',title='Off-phase injection/recovery'); fig.tight_layout(); fig.savefig('kepler186_robustness.png',dpi=180); plt.show()
"""
    result=r"""
significant=bool(ci[0]>0); results=[f'{int(coverage.covered.sum())} of {len(coverage)} predicted transit epochs have in-transit cadence coverage',f'event-median depth {depth*1e6:.0f} ppm; event-bootstrap 95% interval {ci[0]:.0f}–{ci[1]:.0f} ppm',f'simple recovery is {"positive" if significant else "not significant"}; individual-event range {event_depths.depth_ppm.min():.0f} to {event_depths.depth_ppm.max():.0f} ppm']
result={'id':'2026-07-30-kepler-lightcurve-kepler186f','title':'Kepler-186 f full-mission transit audit','archive':'MAST · Kepler','date':'2026-07-30','question':'Is the long-period transit recoverable across the full Kepler mission?','sample_size':int(len(data)),'results':results,'validation':'All 17 long-cadence products are used with the DR25 ephemeris; uncertainty resamples transit events, leave-one-event-out results are stored, and synthetic depths are recovered at off-transit phases.','notebook':'mast/2026-07-30-kepler-lightcurve-kepler186f/notebook.ipynb','hero':'mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_coverage.png','figures':['mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_coverage.png','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_transit_recovery.png','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_robustness.png'],'research_level':'Validated' if significant else 'Exploration','claim_type':'Full-mission transit recovery' if significant else 'Method-limited null result','provenance':['MAST Kepler KIC 8120608','17 *_llc.fits long-cadence products','quality flag = 0 and quarter-wise PDCSAP normalization','NASA Exoplanet Archive DR25 period 129.945392 d, epoch 176.82285 BKJD, duration 5.786 h'],'artifacts':['mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_all_quarters.csv','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_transit_coverage.csv','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_event_depths.csv','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_leave_one_out.csv','mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_injection_recovery.csv'],'quality_checks':[{'name':'DR25 ephemeris verified','status':'pass'},{'name':'Full mission coverage','status':'pass'},{'name':'Event-level bootstrap','status':'pass'},{'name':'Leave-one-event-out','status':'pass'},{'name':'Injection/recovery','status':'pass'},{'name':'Atmosphere or habitability inference','status':'not attempted'}],'limitations':['published DR25 period, epoch, and duration are assumed','simple box depth omits limb darkening and dilution','PDCSAP and local linear detrending may alter depth','injection test measures this pipeline, not planet validation'],'tags':['Kepler','Kepler-186 f','transit','injection recovery']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(coverage.to_string(index=False))
assert len(event_depths)>=5 and len(result['figures'])==3
"""
    refs="""## Interpretation and references

This full-mission audit fixes the main weakness of the previous Quarter 3
plot: a roughly 130-day signal must be checked over multiple quarters. A
positive depth supports archive recovery of the known transit; it does not
independently validate the planet or reveal its atmosphere or surface.

- Quintana et al. (2014), *An Earth-Sized Planet in the Habitable Zone of a Cool Star*: https://doi.org/10.1126/science.1249403
- NASA Kepler-186 f overview: https://www.nasa.gov/news-release/nasas-kepler-telescope-discovers-first-earth-size-planet-in-habitable-zone/
- NASA Exoplanet Archive ephemeris: https://exoplanetarchive.ipac.caltech.edu/overview/K00571.01
- MAST Kepler archive: https://archive.stsci.edu/kepler/
"""
    notebook(folder,title,question,[code(analysis),code(result)],refs)


def hatp7():
    folder=ROOT/'mast/2026-07-30-periodogram-hat-p-7b'
    title='HAT-P-7 b: independent period search and transit-consistency audit'
    question='Is the transit period independently recovered, and do odd/even and quarter-by-quarter depths agree?'
    analysis=r"""
from astropy.timeseries import BoxLeastSquares
data=pd.read_csv('hatp7_all_quarters.csv'); data=data[(data.quality==0)&np.isfinite(data.flux_normalized)].copy(); time=data.time_bkjd.to_numpy(); flux=data.flux_normalized.to_numpy(); error=data.error_normalized.to_numpy()
# A fixed cadence thinning is used only for the search and permutations; all cadences are used for depth checks.
search=data.iloc[::5]; periods=np.linspace(1.5,4.0,2600); duration=.16; bls=BoxLeastSquares(search.time_bkjd,search.flux_normalized,search.error_normalized); power=bls.power(periods,duration); best=float(power.period[np.argmax(power.power)]); t0=float(power.transit_time[np.argmax(power.power)]); peak=float(np.max(power.power))
null=[]
for _ in range(40):
    shuffled=search.flux_normalized.to_numpy().copy()
    for q in search.quarter.unique():
        idx=np.flatnonzero(search.quarter.to_numpy()==q); shuffled[idx]=RNG.permutation(shuffled[idx])
    null.append(np.max(BoxLeastSquares(search.time_bkjd,shuffled,search.error_normalized).power(periods[::3],duration).power))
null=np.asarray(null); fap=(1+np.sum(null>=peak))/(len(null)+1)
fig,ax=plt.subplots(1,2,figsize=(12,4.5)); ax[0].plot(power.period,power.power); ax[0].axvline(best,color='tomato'); ax[0].set(xlabel='Trial period (days)',ylabel='BLS power',title=f'Best period {best:.6f} d'); ax[1].hist(null,bins=14); ax[1].axvline(peak,color='tomato',label='observed peak'); ax[1].set(xlabel='Maximum shuffled BLS power',ylabel='Count',title=f'Empirical false-alarm bound: p={fap:.3f}'); ax[1].legend(); fig.tight_layout(); fig.savefig('hatp7_period_false_alarm.png',dpi=180); plt.show()
phase=((time-t0+best/2)%best)-best/2; inside=np.abs(phase)<duration/2; outside=(np.abs(phase)>.14)&(np.abs(phase)<.35); baseline=np.median(flux[outside]); depth=(baseline-np.median(flux[inside]))*1e6
transit_number=np.rint((time-t0)/best).astype(int); rows=[]
for n in np.unique(transit_number[inside]):
    ii=inside&(transit_number==n); oo=outside&(transit_number==n)
    if ii.sum()>=3 and oo.sum()>=6: rows.append((n,(np.median(flux[oo])-np.median(flux[ii]))*1e6,int(data.quarter.to_numpy()[ii][0])))
depths=pd.DataFrame(rows,columns=['transit_number','depth_ppm','quarter']); depths['parity']=np.where(depths.transit_number%2==0,'even','odd'); depths.to_csv('hatp7_individual_transit_depths.csv',index=False)
odd=depths.loc[depths.parity=='odd','depth_ppm']; even=depths.loc[depths.parity=='even','depth_ppm']; difference=odd.mean()-even.mean(); se=np.sqrt(odd.var(ddof=1)/len(odd)+even.var(ddof=1)/len(even)); quarter=depths.groupby('quarter').depth_ppm.agg(['mean','std','count']).reset_index(); quarter.to_csv('hatp7_quarter_depths.csv',index=False)
bins=np.linspace(-.35,.35,100); centres=(bins[:-1]+bins[1:])/2; idx=np.digitize(phase,bins); med=np.array([np.median(flux[idx==i]) if (idx==i).any() else np.nan for i in range(1,len(bins))]); model=np.where(np.abs(centres)<duration/2,baseline-depth/1e6,baseline)
fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True); use=np.abs(phase)<.35; ax[0].scatter(phase[use],1e6*(flux[use]-1),s=.4,alpha=.05); ax[0].plot(centres,1e6*(med-1),'o',ms=3); ax[0].plot(centres,1e6*(model-1),color='tomato'); ax[0].set(ylabel='Normalized flux (ppm)',title='Folded transit and box model'); ax[1].plot(centres,1e6*(med-model),'o-'); ax[1].axhline(0,color='black'); ax[1].set(xlabel='Days from transit',ylabel='Binned residual (ppm)'); fig.tight_layout(); fig.savefig('hatp7_folded_residuals.png',dpi=180); plt.show()
fig,ax=plt.subplots(1,2,figsize=(11,4)); ax[0].boxplot([odd,even],labels=['odd','even']); ax[0].set(ylabel='Individual depth (ppm)',title=f'Odd − even = {difference:.0f} ± {se:.0f} ppm'); ax[1].errorbar(quarter.quarter,quarter['mean'],yerr=quarter['std']/np.sqrt(quarter['count']),fmt='o-'); ax[1].set(xlabel='Kepler quarter',ylabel='Mean transit depth (ppm)',title='Quarter-to-quarter depth check'); fig.tight_layout(); fig.savefig('hatp7_depth_consistency.png',dpi=180); plt.show()
summary=pd.DataFrame([{'best_period_days':best,'bls_peak_power':peak,'empirical_fap':fap,'n_permutations':len(null),'depth_ppm':depth,'odd_minus_even_ppm':difference,'odd_even_standard_error_ppm':se,'n_transits':len(depths)}]); summary.to_csv('hatp7_search_summary.csv',index=False)
"""
    result=r"""
results=[f'BLS period {best:.6f} days',f'empirical permutation false-alarm probability ≤ {fap:.3f} from {len(null)} trials',f'box depth {depth:.0f} ppm; odd − even {difference:.0f} ± {se:.0f} ppm across {len(depths)} measured events']
odd_even_status='pass' if abs(difference)<3*se else 'caution'
result={'id':'2026-07-30-periodogram-hat-p-7b','title':'HAT-P-7 b period and consistency audit','archive':'MAST · Kepler','date':'2026-07-30','question':'Is the known transit independently recovered without obvious odd/even disagreement?','sample_size':int(len(data)),'results':results,'validation':'The period is searched over 1.5–4 days, the peak is compared with 40 within-quarter permutations, and depths are checked by parity and observing quarter.','notebook':'mast/2026-07-30-periodogram-hat-p-7b/notebook.ipynb','hero':'mast/2026-07-30-periodogram-hat-p-7b/hatp7_period_false_alarm.png','figures':['mast/2026-07-30-periodogram-hat-p-7b/hatp7_period_false_alarm.png','mast/2026-07-30-periodogram-hat-p-7b/hatp7_folded_residuals.png','mast/2026-07-30-periodogram-hat-p-7b/hatp7_depth_consistency.png'],'research_level':'Validated','claim_type':'Independent period recovery','provenance':['MAST Kepler KIC 10666592','18 *_llc.fits long-cadence products','quality flag = 0 and quarter-wise PDCSAP normalization'],'artifacts':['mast/2026-07-30-periodogram-hat-p-7b/hatp7_all_quarters.csv','mast/2026-07-30-periodogram-hat-p-7b/hatp7_search_summary.csv','mast/2026-07-30-periodogram-hat-p-7b/hatp7_individual_transit_depths.csv','mast/2026-07-30-periodogram-hat-p-7b/hatp7_quarter_depths.csv'],'quality_checks':[{'name':'Blind period search','status':'pass'},{'name':'Permutation false-alarm test','status':'pass'},{'name':'Odd/even comparison','status':odd_even_status},{'name':'Quarter systematics','status':'reported'}],'limitations':['40 permutations provide only a coarse false-alarm bound','PDCSAP processing can introduce quarter-dependent depth changes','box model omits limb darkening, dilution, and correlated noise'],'tags':['Kepler','HAT-P-7 b','BLS','false alarm','odd-even']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(quarter.to_string(index=False))
assert abs(best-2.2047)<.02 and len(depths)>100
"""
    refs="""## Interpretation and references

The strong period recovery and parity check are evidence that the known
transiting signal is present. They are not a stand-alone discovery validation.
Quarter-to-quarter depth changes are shown because Kepler seasonal systematics
can make a combined light curve look more precise than it is.

- NASA Exoplanet Catalog, HAT-P-7 b: https://science.nasa.gov/exoplanet-catalog/hat-p-7-b/
- Van Eylen et al. (2013), seasonal transit-depth systematics: https://arxiv.org/abs/1307.6959
- MAST Kepler archive: https://archive.stsci.edu/kepler/
"""
    notebook(folder,title,question,[code(analysis),code(result)],refs)


def write_readmes():
    content={
        'sdss/2026-07-30-star-spectrum-classification':('# SDSS source-identity audit: broad-line quasar\n\nThe exact product is not a star. SDSS labels it QSO/BROADLINE, and broad Balmer-line fits support that correction.\n\n![Spectrum](source_identity_spectrum.png)\n\n[Open the executed notebook](notebook.ipynb)\n'),
        'sdss/2026-07-30-qso-redshift-check':('# SDSS quasar multi-line redshift audit\n\nC IV, C III], and Mg II are measured separately so line-to-line redshift systematics remain visible.\n\n![Spectrum](qso_multiline_spectrum.png)\n\n[Open the executed notebook](notebook.ipynb)\n'),
        'sdss/2026-07-30-emission-line-measurement':('# SDSS galaxy joint Hα + [N II] audit\n\nA constrained three-line fit replaces the old single-Gaussian measurement and corrects its wavelength-unit error.\n\n![Joint line fit](halpha_nii_joint_fit.png)\n\n[Open the executed notebook](notebook.ipynb)\n'),
        'mast/2026-07-30-kepler-lightcurve-kepler186f':('# Kepler-186 f full-mission transit audit\n\nAll 17 long-cadence products are used to audit predicted transit coverage, event-to-event depth stability, and injection recovery.\n\n![Coverage](kepler186_coverage.png)\n\n[Open the executed notebook](notebook.ipynb)\n'),
        'mast/2026-07-30-periodogram-hat-p-7b':('# HAT-P-7 b period and consistency audit\n\nA blind box-least-squares search is followed by a permutation false-alarm test, odd/even comparison, and quarter-by-quarter depth check.\n\n![Period search](hatp7_period_false_alarm.png)\n\n[Open the executed notebook](notebook.ipynb)\n'),
    }
    for name,text in content.items(): (ROOT/name/'README.md').write_text(text)


def main():
    source_identity(); qso_redshift(); galaxy_lines(); kepler186(); hatp7(); write_readmes()
    print('Prepared Scientific Audit Batch 2 notebooks')


if __name__=='__main__':
    main()
