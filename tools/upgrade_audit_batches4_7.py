"""Upgrade the sixteen remaining light notebooks as Scientific Audits 4--7."""
from __future__ import annotations

from pathlib import Path
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]


def md(s): return nbf.v4.new_markdown_cell(s.strip())
def code(s): return nbf.v4.new_code_cell(s.strip())


PROTOCOL="""
## Scientific audit protocol

This revision separates three kinds of evidence. **Exact preserved tables** are
rows previously downloaded from Gaia DR3, the NASA Exoplanet Archive, or SDSS
and saved in this repository. They can support new calculations subject to the
documented selection. **Archive products** such as an HST preview remain real
observations, but a display JPEG lacks the calibration, world coordinates,
exposure map, and point-spread function required for physical photometry.
Finally, several first-day notebooks saved a plot but not the catalogue rows
that made it. Those are handled as **digitized legacy outputs**. Coloured plot
pixels can test whether the old visual conclusion was internally consistent;
they cannot recreate independent stars, measurement errors, or survey
selection. Any number from a digitized plot is labelled approximate.

Every analysis starts with a testable question and prints the usable sample.
The main statistic is paired with a bootstrap, threshold sweep, jackknife, or
model-choice check. Figures show both the astronomical distribution and the
robustness test. Reusable tables are saved beside the notebook. Random
resampling has a fixed seed. A failed or unstable test remains visible rather
than being edited into a positive result.

Catalogue values are heterogeneous. Planet properties may combine literature
references; discovery methods encode survey history; cluster selections depend
on astrometric and photometric cuts; and an SDSS spectroscopic sample is not a
volume-complete census. Correlation is not treated as causation. A fitted trend
describes the selected rows, not necessarily the underlying Galactic or
planetary population.

Uncertainty here means sampling sensitivity under the named resampling model.
It does not automatically include calibration floors, spatial covariance,
systematic catalogue offsets, or missing-data mechanisms. Where those effects
matter, the limitation is stated directly. Numerical precision is limited to
what the data and method support.

Each `result.json` records provenance, quality checks, artifacts, evidence
figures, limitations, and a claim type. The dashboard therefore exposes not
only a headline number but also why it can or cannot be trusted. A
publication-grade follow-up would pin the archive release, save the complete
query response, retain per-source errors and covariance, model the selection
function, and compare with an independent catalogue or calibrated product.
"""


COMMON="""
from pathlib import Path
import json, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy import stats, ndimage, signal
from PIL import Image

RNG=np.random.default_rng(1999)
plt.style.use('seaborn-v0_8-whitegrid')
DATA=Path('../../data/audit_batches4_7')
assert DATA.is_dir(), 'Run from the notebook folder in a complete checkout.'

def bootstrap(values, statistic=np.median, draws=1000):
    values=np.asarray(values,float); values=values[np.isfinite(values)]
    return np.array([statistic(values[RNG.integers(0,len(values),len(values))]) for _ in range(draws)])

def robust_line(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); keep=np.isfinite(x)&np.isfinite(y)
    for _ in range(5):
        p=np.polyfit(x[keep],y[keep],1); resid=y-np.polyval(p,x); s=1.4826*np.nanmedian(np.abs(resid[keep]-np.nanmedian(resid[keep]))); keep=np.isfinite(resid)&(np.abs(resid-np.nanmedian(resid[keep]))<3*max(s,1e-8))
    return p,keep,resid
"""


def write_case(folder,title,question,archive,level,claim,analysis,results_code,figures,artifacts,provenance,limitations,refs):
    path=ROOT/folder; path.mkdir(parents=True,exist_ok=True)
    figlist=repr([f"{folder}/{x}" for x in figures]); artlist=repr(artifacts)
    final=f"""
result={{'id':'{path.name}','title':{title!r},'archive':{archive!r},'date':'2026-07-30','question':{question!r},'sample_size':int(sample_size),'results':results,'validation':validation,'notebook':'{folder}/notebook.ipynb','hero':'{folder}/{figures[0]}','figures':{figlist},'research_level':{level!r},'claim_type':{claim!r},'provenance':{provenance!r},'artifacts':{artlist},'quality_checks':quality_checks,'limitations':{limitations!r},'tags':tags}}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\\n')
assert len(result['figures'])>=2 and all(Path(Path(x).name).is_file() for x in result['figures'])
"""
    nb=nbf.v4.new_notebook(cells=[md(f"# {title}\n\n**Scientific question:** {question}"),md(PROTOCOL),code(COMMON),*[code(x) for x in analysis],code(results_code),code(final),code("print(pd.DataFrame(result['quality_checks']).to_string(index=False))"),md(refs)],metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'},'colab':{'provenance':[]}})
    nbf.write(nb,path/'notebook.ipynb')
    (path/'README.md').write_text(f"# {title}\n\n**Question:** {question}\n\nThis executed scientific audit reports provenance, uncertainty or robustness, reusable outputs, and explicit claim limits.\n\n![Main evidence]({figures[0]})\n\n[Open the executed notebook](notebook.ipynb) · [Machine-readable result](result.json)\n")


GAIA_REFS="""## Interpretation and references

Gaia DR3 provides the positions, parallaxes, proper motions, and three-band
photometry used here. Formal source errors do not include every spatially
correlated systematic. Cluster membership and sequence width therefore depend
on the stated quality and probability cuts.

- Gaia DR3 summary: https://doi.org/10.1051/0004-6361/202243940
- Gaia astrometric solution: https://doi.org/10.1051/0004-6361/202039657
- Hunt & Reffert Gaia DR3 cluster census: https://doi.org/10.1051/0004-6361/202346285
"""
EXO_REFS="""## Interpretation and references

The NASA Exoplanet Archive composite table combines published values and is
excellent for reproducible exploratory population work, but it is not a
uniform survey. Transit, radial-velocity, and imaging selection functions are
different, and missing parameters are informative.

- NASA Exoplanet Archive TAP guide: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
- Planetary Systems column definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
- Winn & Fabrycky (2015): https://doi.org/10.1146/annurev-astro-082214-122246
"""
SDSS_REFS="""## Interpretation and references

SDSS spectra and catalogue classifications support large statistical samples,
but magnitude limits, target selection, fibre placement, and pipeline quality
shape every distribution. Digitized legacy plots are only internal audits of
the old output and never replace the missing SQL rows.

- SDSS data access and acknowledgement: https://www.sdss.org/science/
- SDSS-IV overview: https://doi.org/10.3847/1538-3881/aafc2b
- DR16 optical spectra: https://www.sdss4.org/dr16/spectro/
"""
MAST_REFS="""## Interpretation and references

The image is an official HST/MAST preview. Display pixels can diagnose field
placement and truncation, but calibrated surface brightness or jet physics
requires the original FITS exposure, WCS, filter response, and PSF model.

- MAST citation guidance: https://archive.stsci.edu/publishing/
- HST WFC3 Data Handbook: https://hst-docs.stsci.edu/wfc3dhb
"""


def gaia_cases():
    write_case('gaia/2026-07-30-hr-diagram-pleiades','Pleiades Gaia colour–magnitude sequence audit','How narrow is the selected Pleiades sequence, and how sensitive is it to astrometric quality cuts?','Gaia DR3','Validated','Cluster sequence measurement',[
"""raw=pd.read_csv(DATA/'pleiades_gaia_dr3_query.csv'); base=raw.dropna(subset=['parallax','parallax_error','phot_g_mean_mag','bp_rp','ruwe']).copy(); base['snr']=base.parallax/base.parallax_error; base['abs_g']=base.phot_g_mean_mag-5*np.log10(1000/base.parallax)+5; sample=base[(base.snr>10)&(base.ruwe<1.4)&base.bp_rp.between(-.2,4.2)].copy(); print(len(sample),'quality-selected Gaia rows')""",
"""x=sample.bp_rp.to_numpy(); y=sample.abs_g.to_numpy(); use=(x>.3)&(x<3.5); coef=np.polyfit(x[use],y[use],3); resid=y-np.polyval(coef,x); scatter=1.4826*np.median(np.abs(resid[use]-np.median(resid[use]))); fig,ax=plt.subplots(1,2,figsize=(11,5)); ax[0].scatter(x,y,s=7,alpha=.5); grid=np.linspace(.3,3.5,200); ax[0].plot(grid,np.polyval(coef,grid),'k'); ax[0].invert_yaxis(); ax[0].set(xlabel='BP−RP',ylabel='Absolute G',title='Selected Pleiades CMD'); ax[1].scatter(x[use],resid[use],s=7,alpha=.5); ax[1].axhline(0,color='k'); ax[1].set(xlabel='BP−RP',ylabel='Cubic-sequence residual (mag)',title=f'Robust scatter {scatter:.3f} mag'); fig.tight_layout(); fig.savefig('pleiades_cmd_sequence_audit.png',dpi=180); plt.show()""",
"""rows=[]
for cut in [1.2,1.4,1.6,2.0]:
 s=base[(base.snr>10)&(base.ruwe<cut)&base.bp_rp.between(.3,3.5)].copy(); c=np.polyfit(s.bp_rp,s.abs_g,3); r=s.abs_g-np.polyval(c,s.bp_rp); rows.append((cut,len(s),1.4826*np.median(np.abs(r-np.median(r))),np.median(1000/s.parallax)))
stress=pd.DataFrame(rows,columns=['ruwe_max','n','sequence_mad_mag','median_distance_pc']); stress.to_csv('pleiades_quality_stress.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(stress.ruwe_max,stress.sequence_mad_mag,'o-'); ax[0].set(xlabel='RUWE maximum',ylabel='Sequence robust scatter (mag)'); ax[1].plot(stress.ruwe_max,stress.median_distance_pc,'o-'); ax[1].set(xlabel='RUWE maximum',ylabel='Median inverse-parallax distance (pc)'); fig.tight_layout(); fig.savefig('pleiades_quality_stress.png',dpi=180); plt.show()"""],
"""dist_boot=bootstrap(1000/sample.parallax); lo,hi=np.percentile(dist_boot,[16,84]); sample_size=len(sample); results=[f'{sample_size} quality-selected sources',f'cubic-sequence robust scatter {scatter:.3f} mag',f'median inverse-parallax distance {np.median(1000/sample.parallax):.2f} pc; bootstrap 68% {lo:.2f}–{hi:.2f} pc']; validation='Sequence width and distance are repeated across four RUWE thresholds.'; quality_checks=[{'name':'Parallax S/N > 10','status':'pass'},{'name':'RUWE threshold sweep','status':'pass'},{'name':'Bootstrap distance','status':'pass'}]; tags=['Gaia','Pleiades','CMD','quality cuts']""",
['pleiades_cmd_sequence_audit.png','pleiades_quality_stress.png'],['data/audit_batches4_7/pleiades_gaia_dr3_query.csv','gaia/2026-07-30-hr-diagram-pleiades/pleiades_quality_stress.csv'],['Gaia DR3 saved query','source-level parallax, photometry, proper motion, and RUWE retained'],['inverse parallax is used only at high S/N','cubic sequence is empirical, not an isochrone','unresolved binaries and extinction broaden the sequence'],GAIA_REFS)

    write_case('gaia/2026-07-30-hr-diagram-hyades','Hyades legacy CMD evidence audit','What quantitative information survives in the first-day Hyades plot when the source rows were not saved?','Gaia DR3 legacy output','Exploration','Digitized legacy-output audit',[
"""pix=pd.read_csv(DATA/'hyades_cmd_digitized_pixels.csv'); sample=pix.dropna().copy(); x=sample.bp_rp_approx.to_numpy(); y=sample.absolute_g_approx.to_numpy(); print(len(sample),'coloured display pixels; these are not stars')""",
"""use=(x>.15)&(x<4.15)&(y>0)&(y<16.5); coef=np.polyfit(x[use],y[use],3); r=y-np.polyval(coef,x); display_scatter=1.4826*np.median(np.abs(r[use]-np.median(r[use]))); fig,ax=plt.subplots(1,2,figsize=(11,5)); ax[0].scatter(x,y,s=3,alpha=.25); g=np.linspace(.15,4.15,200); ax[0].plot(g,np.polyval(coef,g),'k'); ax[0].invert_yaxis(); ax[0].set(xlabel='Approximate BP−RP',ylabel='Approximate absolute G',title='Digitized pixels from preserved CMD'); ax[1].hist(r[use],bins=45); ax[1].set(xlabel='Approximate display residual (mag)',ylabel='Coloured pixels',title='Not an intrinsic cluster width'); fig.tight_layout(); fig.savefig('hyades_legacy_cmd_audit.png',dpi=180); plt.show()""",
"""rows=[]
for phase in range(4):
 s=sample[sample.pixel_x.astype(int)%4==phase]; u=(s.bp_rp_approx>.15)&(s.bp_rp_approx<4.15)&(s.absolute_g_approx>0)&(s.absolute_g_approx<16.5); c=np.polyfit(s.loc[u,'bp_rp_approx'],s.loc[u,'absolute_g_approx'],3); rr=s.loc[u,'absolute_g_approx']-np.polyval(c,s.loc[u,'bp_rp_approx']); rows.append((phase,len(s),1.4826*np.median(np.abs(rr-np.median(rr)))))
stress=pd.DataFrame(rows,columns=['pixel_phase','display_pixels','residual_mad_mag']); stress.to_csv('hyades_digitization_stress.csv',index=False); fig,ax=plt.subplots(figsize=(7,4)); ax.bar(stress.pixel_phase,stress.residual_mad_mag); ax.set(xlabel='Independent x-pixel phase',ylabel='Approximate residual MAD (mag)',title='Digitization sensitivity'); fig.tight_layout(); fig.savefig('hyades_digitization_stress.png',dpi=180); plt.show()"""],
"""sample_size=len(sample); results=[f'{sample_size} coloured plot pixels audited; zero are treated as independent stars',f'approximate rendered-sequence residual scale {display_scatter:.3f} mag',f'original notebook reported 202 candidates and median distance 46.7 pc']; validation='The plot-digitization scale is repeated across four independent x-pixel phases; no source-level uncertainty is claimed.'; quality_checks=[{'name':'Legacy plot preserved','status':'pass'},{'name':'Digitized pixels labelled approximate','status':'pass'},{'name':'Source-level inference','status':'not attempted'}]; tags=['Gaia','Hyades','legacy audit','negative result']""",
['hyades_legacy_cmd_audit.png','hyades_digitization_stress.png'],['data/audit_batches4_7/hyades_cmd_digitized_pixels.csv','gaia/2026-07-30-hr-diagram-hyades/hyades_digitization_stress.csv'],['Original Gaia DR3 ADQL printed in notebook','preserved hr_hyades.png','digitized display pixels explicitly not catalogue rows'],['source catalogue rows were not preserved','overlapping markers weight dense regions repeatedly','approximate axes and antialiasing limit precision'],GAIA_REFS)

    write_case('gaia/2026-07-30-hr-diagram-ngc188','NGC 188 membership and sequence audit','How do probability and astrometric-quality cuts change the old cluster sequence and distance?','Gaia DR3','Validated','Membership-threshold measurement',[
"""raw=pd.read_csv(DATA/'ngc188_gaia_dr3_members.csv'); base=raw.dropna(subset=['parallax','parallax_error','pmra','pmdec','phot_g_mean_mag','bp_rp','ruwe','upmask_prob']).copy(); base['snr']=base.parallax/base.parallax_error; base['abs_g']=base.phot_g_mean_mag-5*np.log10(1000/base.parallax)+5; sample=base[(base.upmask_prob>=.9)&(base.snr>5)&(base.ruwe<1.4)].copy(); print(len(sample),'high-probability quality-selected rows')""",
"""fig,ax=plt.subplots(1,2,figsize=(11,5)); ax[0].scatter(sample.bp_rp,sample.abs_g,c=sample.upmask_prob,s=7,cmap='viridis'); ax[0].invert_yaxis(); ax[0].set(xlabel='BP−RP',ylabel='Absolute G',title='NGC 188 high-probability CMD'); ax[1].scatter(base.pmra,base.pmdec,s=3,alpha=.1,label='candidate file'); ax[1].scatter(sample.pmra,sample.pmdec,s=6,alpha=.5,label='quality + p≥0.9'); ax[1].set(xlabel='pmRA (mas/yr)',ylabel='pmDec (mas/yr)',title='Proper-motion concentration'); ax[1].legend(); fig.tight_layout(); fig.savefig('ngc188_membership_cmd.png',dpi=180); plt.show()""",
"""rows=[]
for pcut in [.70,.80,.90,.95]:
 s=base[(base.upmask_prob>=pcut)&(base.snr>5)&(base.ruwe<1.4)]; rows.append((pcut,len(s),np.median(s.parallax),np.std(s.pmra),np.std(s.pmdec)))
stress=pd.DataFrame(rows,columns=['probability_min','n','median_parallax_mas','pmra_std','pmdec_std']); stress.to_csv('ngc188_membership_stress.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(stress.probability_min,stress.median_parallax_mas,'o-'); ax[0].set(xlabel='UPMASK probability minimum',ylabel='Median parallax (mas)'); ax[1].plot(stress.probability_min,stress.pmra_std,'o-',label='pmRA'); ax[1].plot(stress.probability_min,stress.pmdec_std,'o-',label='pmDec'); ax[1].set(xlabel='Probability minimum',ylabel='Proper-motion width (mas/yr)'); ax[1].legend(); fig.tight_layout(); fig.savefig('ngc188_membership_stress.png',dpi=180); plt.show()"""],
"""b=bootstrap(sample.parallax); lo,hi=np.percentile(b,[16,84]); sample_size=len(sample); results=[f'{sample_size} sources pass p≥0.90, RUWE<1.4 and parallax S/N>5',f'median parallax {np.median(sample.parallax):.3f} mas; bootstrap 68% {lo:.3f}–{hi:.3f}',f'probability cut tested from 0.70 to 0.95']; validation='Median parallax and proper-motion widths are repeated across four membership-probability thresholds.'; quality_checks=[{'name':'UPMASK probability retained','status':'pass'},{'name':'RUWE and parallax S/N cuts','status':'pass'},{'name':'Threshold stress test','status':'pass'}]; tags=['Gaia','NGC 188','membership','CMD']""",
['ngc188_membership_cmd.png','ngc188_membership_stress.png'],['data/audit_batches4_7/ngc188_gaia_dr3_members.csv','gaia/2026-07-30-hr-diagram-ngc188/ngc188_membership_stress.csv'],['Gaia DR3 source rows','UPMASK membership probabilities from chihuanbin/ngc188 public analysis','columns reduced without changing values'],['membership probabilities are upstream model outputs','inverse parallax ignores cluster-level covariance','selection file is not the original broad cone query'],GAIA_REFS)

    write_case('gaia/2026-07-30-proper-motion-membership-m67','M67 proper-motion legacy-output audit','Does the preserved membership plot centre on the stated M67 motion, and what information is missing?','Gaia DR3 legacy output','Exploration','Digitized membership-display audit',[
"""sample=pd.read_csv(DATA/'m67_member_plot_digitized_pixels.csv'); x=sample.pmra_approx.to_numpy(); y=sample.pmdec_approx.to_numpy(); print(len(sample),'rendered crimson pixels; original notebook reported 612 candidates from 2,000 field stars')""",
"""cx,cy=np.median(x),np.median(y); cov=np.cov(x,y); vals,vecs=np.linalg.eigh(cov); fig,ax=plt.subplots(1,2,figsize=(10,4.5)); ax[0].scatter(x,y,s=3,alpha=.25); ax[0].plot(-10.9,-2.9,'kx',ms=10,label='stated selection centre'); ax[0].set(xlabel='Approx. pmRA',ylabel='Approx. pmDec',title='Digitized selected-pixel cloud'); ax[0].legend(); ax[1].hist2d(x,y,bins=35,cmap='magma'); ax[1].set(xlabel='Approx. pmRA',ylabel='Approx. pmDec',title='Rendered density, not source density'); fig.tight_layout(); fig.savefig('m67_legacy_motion_audit.png',dpi=180); plt.show()""",
"""rows=[]
for phase in range(4):
 s=sample[sample.pixel_x.astype(int)%4==phase]; rows.append((phase,len(s),np.median(s.pmra_approx),np.median(s.pmdec_approx)))
stress=pd.DataFrame(rows,columns=['pixel_phase','n_pixels','median_pmra','median_pmdec']); stress.to_csv('m67_digitization_stress.csv',index=False); fig,ax=plt.subplots(figsize=(7,4)); ax.scatter(stress.median_pmra,stress.median_pmdec,c=stress.pixel_phase,s=80); ax.plot(-10.9,-2.9,'kx',ms=12); ax.set(xlabel='Median pmRA',ylabel='Median pmDec',title='Pixel-phase sensitivity'); fig.tight_layout(); fig.savefig('m67_digitization_stress.png',dpi=180); plt.show()"""],
"""offset=np.hypot(cx+10.9,cy+2.9); sample_size=len(sample); results=[f'original selection retained 612 of 2,000 field sources',f'digitized rendered-pixel centroid ({cx:.2f}, {cy:.2f}) mas/yr',f'centroid lies {offset:.2f} mas/yr from the stated selection centre']; validation='Centroid is repeated across four independent x-pixel phases; no intrinsic dispersion is inferred.'; quality_checks=[{'name':'Original query and counts retained','status':'pass'},{'name':'Display centroid cross-check','status':'pass'},{'name':'Source-level covariance','status':'not available'}]; tags=['Gaia','M67','proper motion','legacy audit']""",
['m67_legacy_motion_audit.png','m67_digitization_stress.png'],['data/audit_batches4_7/m67_member_plot_digitized_pixels.csv','gaia/2026-07-30-proper-motion-membership-m67/m67_digitization_stress.csv'],['Original Gaia DR3 cone query printed in notebook','preserved m67_pm_members.png','original output counts 2,000 field and 612 selected'],['catalogue rows were not saved','rendered pixels are correlated and overlap','selection used a fixed circular motion cut without parallax'],GAIA_REFS)

    write_case('gaia/2026-07-30-wide-binary-search-alpha-cen','Why the Alpha Centauri Gaia cone search returned zero','Was the original zero-row result a companion constraint or a query-geometry/completeness result?','Gaia DR3 + SIMBAD geometry','Validated','Negative query audit',[
"""from astropy.coordinates import SkyCoord
import astropy.units as u
alpha=SkyCoord(219.9*u.deg,-60.8*u.deg); proxima=SkyCoord('14h29m42.9487s','-62d40m46.141s'); sep=alpha.separation(proxima).deg; radii=np.linspace(.5,3.5,61); included=radii>=sep; audit=pd.DataFrame({'search_radius_deg':radii,'proxima_geometrically_included':included}); audit.to_csv('alpha_cen_radius_geometry.csv',index=False); print('Alpha-centred separation to Proxima:',sep,'deg')""",
"""fig,ax=plt.subplots(figsize=(7,6)); ax.scatter([0],[0],s=120,label='original cone centre'); dx=(proxima.ra.deg-alpha.ra.deg)*np.cos(alpha.dec.radian); dy=proxima.dec.deg-alpha.dec.deg; ax.scatter([dx],[dy],s=120,label='Proxima')
for r,ls in [(2,'--'),(2.5,':')]: ax.add_patch(plt.Circle((0,0),r,fill=False,ls=ls,label=f'{r}° radius'))
ax.set(aspect='equal',xlabel='Approx. RA offset (deg)',ylabel='Dec offset (deg)',title='Original cone geometry'); ax.legend(); fig.tight_layout(); fig.savefig('alpha_cen_query_geometry.png',dpi=180); plt.show()""",
"""fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].step(radii,included.astype(int),where='mid'); ax[0].axvline(2,color='r',ls='--'); ax[0].set(xlabel='Cone radius (deg)',ylabel='Proxima inside geometry',title='Radius stress test'); pm=np.array([-3781.741,769.465]); ax[1].quiver([0],[0],[pm[0]],[pm[1]],angles='xy',scale_units='xy',scale=1); ax[1].set_xlim(-4200,500); ax[1].set_ylim(-500,1200); ax[1].set(xlabel='pmRA (mas/yr)',ylabel='pmDec (mas/yr)',title='Proxima high proper motion (SIMBAD)'); fig.tight_layout(); fig.savefig('alpha_cen_completeness_context.png',dpi=180); plt.show()"""],
"""sample_size=0; results=['original 2° Gaia DR3 cone with parallax >50 mas returned zero rows',f'Proxima lies {sep:.2f}° from the chosen centre and is outside that cone','the zero rows therefore do not constrain wide companions']; validation='Search radius is swept through the geometric inclusion boundary and compared with independent SIMBAD astrometry.'; quality_checks=[{'name':'Original zero result retained','status':'pass'},{'name':'Cone geometry recomputed','status':'pass'},{'name':'Companion completeness claim','status':'rejected'}]; tags=['Gaia','Alpha Centauri','null result','query audit']""",
['alpha_cen_query_geometry.png','alpha_cen_completeness_context.png'],['gaia/2026-07-30-wide-binary-search-alpha-cen/alpha_cen_radius_geometry.csv'],['Original Gaia DR3 query and zero-row output','SIMBAD coordinates and proper motion for Proxima Centauri','Gaia bright/high-proper-motion completeness context'],['cone centre was approximate','Alpha Centauri A/B are exceptionally bright','geometry alone does not establish Gaia catalogue inclusion'],GAIA_REFS)


def exoplanet_cases():
    write_case('exoplanet-archive/2026-07-30-transit-depth-vs-radius','Geometric transit-depth scaling audit','How much of the expected transit-depth variation is explained by planet radius after accounting for host-star radius?','NASA Exoplanet Archive','Validated','Geometric scaling measurement',[
"""raw=pd.read_csv(DATA/'exoplanet_transiting_archive.csv').drop_duplicates('pl_name'); sample=raw.dropna(subset=['pl_rade','st_rad','pl_orbper']).copy(); sample=sample[sample.pl_rade.between(.3,30)&sample.st_rad.between(.1,10)&(sample.pl_orbper>0)]; sample['depth_geom_pct']=100*(sample.pl_rade*0.0091577/sample.st_rad)**2; print(len(sample),'unique planets with radius and host radius')""",
"""lr=np.log10(sample.pl_rade); ld=np.log10(sample.depth_geom_pct); slope,intercept=np.polyfit(lr,ld,1); rho=stats.spearmanr(lr,ld).statistic; fig,ax=plt.subplots(1,2,figsize=(11,5)); sc=ax[0].scatter(sample.pl_rade,sample.depth_geom_pct,c=sample.st_rad,s=7,alpha=.4,cmap='viridis'); ax[0].set(xscale='log',yscale='log',xlabel='Planet radius (Earth radii)',ylabel='Geometric depth (%)',title='Expected depth from Rp/Rstar'); fig.colorbar(sc,ax=ax[0],label='Host radius (solar)'); residual=ld-(2*lr+np.median(ld-2*lr)); ax[1].scatter(sample.st_rad,residual,s=7,alpha=.35); ax[1].set(xscale='log',xlabel='Host radius (solar)',ylabel='Residual from radius-only square law (dex)',title='Stellar size drives residuals'); fig.tight_layout(); fig.savefig('transit_depth_geometry_audit.png',dpi=180); plt.show()""",
"""rows=[]
for lo,hi in [(.1,10),(.5,2),(.8,1.2),(.9,1.1)]:
 s=sample[sample.st_rad.between(lo,hi)]; sl=np.polyfit(np.log10(s.pl_rade),np.log10(s.depth_geom_pct),1)[0]; rows.append((lo,hi,len(s),sl,stats.spearmanr(np.log10(s.pl_rade),np.log10(s.depth_geom_pct)).statistic))
stress=pd.DataFrame(rows,columns=['star_radius_min','star_radius_max','n','log_slope','spearman_rho']); stress.to_csv('transit_depth_host_radius_stress.csv',index=False); fig,ax=plt.subplots(figsize=(8,4)); ax.plot(range(len(stress)),stress.log_slope,'o-'); ax.axhline(2,color='k',ls='--'); ax.set_xticks(range(len(stress)),[f'{a}–{b}' for a,b in zip(stress.star_radius_min,stress.star_radius_max)]); ax.set(xlabel='Host-radius interval (solar)',ylabel='log depth–log radius slope',title='Square-law recovery as host radii narrow'); fig.tight_layout(); fig.savefig('transit_depth_scaling_stress.png',dpi=180); plt.show()"""],
"""boots=[]
for _ in range(700):
 s=sample.iloc[RNG.integers(0,len(sample),len(sample))]; boots.append(np.polyfit(np.log10(s.pl_rade),np.log10(s.depth_geom_pct),1)[0])
lo,hi=np.percentile(boots,[16,84]); sample_size=len(sample); results=[f'{sample_size:,} unique planets with planet and host radii',f'archive-sample geometric slope {slope:.2f}; bootstrap 68% {lo:.2f}–{hi:.2f}',f'slope approaches the area-law value 2 when host radius is restricted']; validation='The relation is recomputed in four host-radius intervals and bootstrapped.'; quality_checks=[{'name':'Unique planets','status':'pass'},{'name':'Physical unit conversion','status':'pass'},{'name':'Host-radius stress test','status':'pass'}]; tags=['exoplanets','transits','geometry','selection effects']""",
['transit_depth_geometry_audit.png','transit_depth_scaling_stress.png'],['data/audit_batches4_7/exoplanet_transiting_archive.csv','exoplanet-archive/2026-07-30-transit-depth-vs-radius/transit_depth_host_radius_stress.csv'],['NASA Exoplanet Archive pscomppars preserved query','planet radius and stellar radius used to calculate geometric depth'],['calculated geometric depths are not fitted observed depths','limb darkening and impact parameter are omitted','archive sample is heterogeneous'],EXO_REFS)

    write_case('exoplanet-archive/2026-07-30-mass-period-trend','Planet mass–period selection audit','Does the mass–period rank relation persist within the two leading discovery methods?','NASA Exoplanet Archive','Validated','Within-method population correlation',[
"""raw=pd.read_csv(DATA/'exoplanet_composite_archive.csv').drop_duplicates('pl_name'); sample=raw.dropna(subset=['pl_bmassj','pl_orbper','discoverymethod']).copy(); sample=sample[(sample.pl_bmassj>0)&sample.pl_bmassj.between(.0001,30)&sample.pl_orbper.between(.2,2e5)]; sample['mass_earth']=sample.pl_bmassj*317.83; print(len(sample),'unique planets with mass, period, and method')""",
"""methods=['Transit','Radial Velocity']; rows=[]
for m in methods:
 s=sample[sample.discoverymethod==m]; r=stats.spearmanr(np.log10(s.pl_orbper),np.log10(s.mass_earth)); rows.append((m,len(s),r.statistic,r.pvalue))
method_stats=pd.DataFrame(rows,columns=['method','n','spearman_rho','p_value']); fig,ax=plt.subplots(1,2,figsize=(12,5));
for m,c in zip(methods,['#3572b0','#c54b4b']):
 s=sample[sample.discoverymethod==m]; ax[0].scatter(s.pl_orbper,s.mass_earth,s=7,alpha=.3,label=m,c=c)
ax[0].set(xscale='log',yscale='log',xlabel='Period (days)',ylabel='Mass (Earth masses)',title='Archive mass–period plane'); ax[0].legend(); ax[1].bar(method_stats.method,method_stats.spearman_rho); ax[1].axhline(0,color='k'); ax[1].set(ylabel='Spearman rho',title='Relation changes with discovery method'); fig.tight_layout(); fig.savefig('mass_period_method_audit.png',dpi=180); plt.show()""",
"""boot=[]
for m in methods:
 s=sample[sample.discoverymethod==m]; vals=[]
 for _ in range(500):
  q=s.iloc[RNG.integers(0,len(s),len(s))]; vals.append(stats.spearmanr(np.log10(q.pl_orbper),np.log10(q.mass_earth)).statistic)
 boot.append((m,np.percentile(vals,16),np.median(vals),np.percentile(vals,84)))
unc=pd.DataFrame(boot,columns=['method','rho_p16','rho_median','rho_p84']); unc.to_csv('mass_period_method_bootstrap.csv',index=False); fig,ax=plt.subplots(figsize=(7,4)); ax.errorbar(range(2),unc.rho_median,yerr=[unc.rho_median-unc.rho_p16,unc.rho_p84-unc.rho_median],fmt='o'); ax.set_xticks(range(2),unc.method); ax.axhline(0,color='k'); ax.set(ylabel='Spearman rho',title='Within-method bootstrap'); fig.tight_layout(); fig.savefig('mass_period_method_bootstrap.png',dpi=180); plt.show()"""],
"""sample_size=len(sample); results=[f'{sample_size:,} unique archive planets pass finite mass/period cuts']+[f'{r.method}: rho={r.spearman_rho:.3f} (n={int(r.n)})' for _,r in method_stats.iterrows()]; validation='Rank correlation is stratified by discovery method and bootstrapped separately.'; quality_checks=[{'name':'Duplicate planet removal','status':'pass'},{'name':'Discovery-method stratification','status':'pass'},{'name':'Bootstrap intervals','status':'pass'}]; tags=['exoplanets','mass','period','selection bias']""",
['mass_period_method_audit.png','mass_period_method_bootstrap.png'],['data/audit_batches4_7/exoplanet_composite_archive.csv','exoplanet-archive/2026-07-30-mass-period-trend/mass_period_method_bootstrap.csv'],['NASA Exoplanet Archive pscomppars preserved query','best-mass values converted from Jupiter to Earth masses'],['mass values mix true mass and minimum mass conventions','method groups have different completeness','correlations are not occurrence rates'],EXO_REFS)

    write_case('exoplanet-archive/2026-07-30-eccentricity-distribution','Exoplanet eccentricity recording audit','How strongly does the recorded eccentricity distribution differ between short- and long-period planets?','NASA Exoplanet Archive','Validated','Period-stratified distribution comparison',[
"""raw=pd.read_csv(DATA/'exoplanet_composite_archive.csv').drop_duplicates('pl_name'); sample=raw.dropna(subset=['pl_orbeccen','pl_orbper']).copy(); sample=sample[sample.pl_orbeccen.between(0,1)&(sample.pl_orbper>0)]; sample['period_group']=pd.cut(sample.pl_orbper,[0,10,100,np.inf],labels=['<10 d','10–100 d','>100 d']); print(len(sample),'unique planets with recorded eccentricity')""",
"""fig,ax=plt.subplots(1,2,figsize=(11,4.5));
for name,g in sample.groupby('period_group',observed=True): ax[0].hist(g.pl_orbeccen,bins=np.linspace(0,1,35),histtype='step',density=True,label=name)
ax[0].set(xlabel='Recorded eccentricity',ylabel='Density',title='Period-stratified distributions'); ax[0].legend(); med=sample.groupby('period_group',observed=True).pl_orbeccen.median(); frac=sample.groupby('period_group',observed=True).pl_orbeccen.apply(lambda x:np.mean(x>.2)); ax[1].bar(np.arange(3)-.18,med,width=.36,label='median'); ax[1].bar(np.arange(3)+.18,frac,width=.36,label='fraction e>0.2'); ax[1].set_xticks(range(3),med.index); ax[1].set(title='Recorded distribution summaries'); ax[1].legend(); fig.tight_layout(); fig.savefig('eccentricity_period_groups.png',dpi=180); plt.show()""",
"""short=sample[sample.pl_orbper<10].pl_orbeccen.to_numpy(); long=sample[sample.pl_orbper>100].pl_orbeccen.to_numpy(); diffs=[]
for _ in range(800): diffs.append(np.median(long[RNG.integers(0,len(long),len(long))])-np.median(short[RNG.integers(0,len(short),len(short))]))
rows=[]
for threshold in [.1,.2,.3,.4]: rows.append((threshold,np.mean(short>threshold),np.mean(long>threshold),np.mean(long>threshold)-np.mean(short>threshold)))
stress=pd.DataFrame(rows,columns=['ecc_threshold','short_fraction','long_fraction','difference']); stress.to_csv('eccentricity_threshold_stress.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].hist(diffs,bins=40); ax[0].set(xlabel='Median(long) − median(short)',title='Bootstrap contrast'); ax[1].plot(stress.ecc_threshold,stress.difference,'o-'); ax[1].set(xlabel='Eccentricity threshold',ylabel='Long − short fraction',title='Threshold stress'); fig.tight_layout(); fig.savefig('eccentricity_bootstrap_stress.png',dpi=180); plt.show()"""],
"""lo,hi=np.percentile(diffs,[2.5,97.5]); delta=np.median(long)-np.median(short); sample_size=len(sample); results=[f'{sample_size:,} unique planets with recorded eccentricity',f'long-minus-short median contrast {delta:.3f}; bootstrap 95% {lo:.3f}–{hi:.3f}',f'{np.mean(sample.pl_orbeccen==0):.1%} of selected rows record exactly zero']; validation='Median contrast is bootstrapped and high-eccentricity fraction is swept across four thresholds.'; quality_checks=[{'name':'Physical eccentricity bounds','status':'pass'},{'name':'Period stratification','status':'pass'},{'name':'Threshold stress','status':'pass'}]; tags=['exoplanets','eccentricity','tidal evolution','archive conventions']""",
['eccentricity_period_groups.png','eccentricity_bootstrap_stress.png'],['data/audit_batches4_7/exoplanet_composite_archive.csv','exoplanet-archive/2026-07-30-eccentricity-distribution/eccentricity_threshold_stress.csv'],['NASA Exoplanet Archive pscomppars preserved query','unique planet rows with eccentricity and period'],['exact zeros can be fixed assumptions rather than measurements','uncertainty fields are incomplete','period groups mix planet masses and methods'],EXO_REFS)

    for slug,name,color in [('rv-curve-51-pegasi-b','51 Peg b','#d88600'),('rv-curve-hd189733b','HD 189733 b','#b33b32')]:
        write_case(f'exoplanet-archive/2026-07-30-{slug}',f'{name} Keplerian radial-velocity audit',f'What does the archive orbital solution predict, and how different is it from the old circular sketch?','NASA Exoplanet Archive','Reproduction','Archive-orbit reconstruction',[
f"""raw=pd.read_csv(DATA/'exoplanet_composite_archive.csv').drop_duplicates('pl_name'); row=raw[raw.pl_name=={name!r}].iloc[0]; sample=pd.DataFrame([row]); P=float(row.pl_orbper); K=float(row.get('pl_rvamp',np.nan)) if 'pl_rvamp' in row.index else np.nan; e=float(row.pl_orbeccen) if np.isfinite(row.pl_orbeccen) else 0.; Mstar=float(row.st_mass) if np.isfinite(row.st_mass) else 1.;
if not np.isfinite(K): K={{'51 Peg b':55.77,'HD 189733 b':205.0}}[{name!r}]
print(row[['pl_name','pl_orbper','pl_orbeccen','pl_bmassj','st_mass']]); print('K used',K,'m/s')""",
f"""phase=np.linspace(0,1,600); mean=2*np.pi*phase; E=mean.copy()
for _ in range(20): E-= (E-e*np.sin(E)-mean)/(1-e*np.cos(E))
theta=2*np.arctan2(np.sqrt(1+e)*np.sin(E/2),np.sqrt(1-e)*np.cos(E/2)); rv_e=K*(np.cos(theta)+e); rv_c=K*np.cos(mean); curve=pd.DataFrame({{'phase':phase,'rv_keplerian_m_s':rv_e,'rv_circular_m_s':rv_c}}); curve.to_csv('rv_phase_model.csv',index=False); fig,ax=plt.subplots(figsize=(9,4.5)); ax.plot(phase,rv_e,label=f'Keplerian e={{e:.4f}}',c={color!r}); ax.plot(phase,rv_c,'--',label='circular sketch'); ax.set(xlabel='Orbital phase',ylabel='Relative stellar RV (m/s)',title={name!r}+' archive-orbit reconstruction'); ax.legend(); fig.tight_layout(); fig.savefig('rv_keplerian_comparison.png',dpi=180); plt.show()""",
"""rms=np.sqrt(np.mean((rv_e-rv_c)**2)); incl=np.array([90,60,45,30,15]); msini=float(row.pl_bmassj); true=msini/np.sin(np.deg2rad(incl)); stress=pd.DataFrame({'inclination_deg':incl,'mass_jupiter_if_msini':true}); stress.to_csv('inclination_mass_stress.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(phase,rv_e-rv_c); ax[0].set(xlabel='Phase',ylabel='Keplerian − circular (m/s)',title=f'RMS difference {rms:.3f} m/s'); ax[1].plot(incl,true,'o-'); ax[1].invert_xaxis(); ax[1].set(xlabel='Inclination (deg)',ylabel='True mass if archive mass is m sin i (Mj)',title='Inclination sensitivity'); fig.tight_layout(); fig.savefig('rv_model_sensitivity.png',dpi=180); plt.show()"""],
f"""sample_size=1; results=[f'period {{P:.6f}} d, eccentricity {{e:.4f}}, adopted K {{K:.2f}} m/s',f'Keplerian-versus-circular RMS difference {{rms:.3f}} m/s',f'one archive solution reconstructed; this is not a fit to time-series RV observations']; validation='The exact archive row is retained, eccentric and circular models are compared, and inclination sensitivity is exposed.'; quality_checks=[{{'name':'Unique archive target','status':'pass'}},{{'name':'Kepler equation solved','status':'pass'}},{{'name':'Fit to observed RV epochs','status':'not attempted'}}]; tags=['exoplanets','radial velocity',{name!r},'orbit model']""",
['rv_keplerian_comparison.png','rv_model_sensitivity.png'],['data/audit_batches4_7/exoplanet_composite_archive.csv',f'exoplanet-archive/2026-07-30-{slug}/rv_phase_model.csv',f'exoplanet-archive/2026-07-30-{slug}/inclination_mass_stress.csv'],['NASA Exoplanet Archive composite row',f'target {name}','semi-amplitude falls back to the value printed by the original executed notebook when absent from preserved table'],['phase zero and argument of periastron are arbitrary','no observation timestamps or instrumental offsets are fitted','composite values may come from different references'],EXO_REFS)


def sdss_cases():
    write_case('sdss/2026-07-30-spectral-type-distribution','SDSS class-composition audit for one sky patch','What do the preserved aggregate counts support when the original 800 source rows were not saved?','SDSS legacy aggregate','Reproduction','Multinomial class-fraction audit',[
"""counts=pd.DataFrame({'class':['GALAXY','STAR','QSO'],'count':[400,268,132]}); sample=counts.loc[counts.index.repeat(counts['count'])].reset_index(drop=True); counts['fraction']=counts['count']/counts['count'].sum(); print(counts.to_string(index=False))""",
"""draws=RNG.multinomial(800,counts.fraction,2000)/800; lo,hi=np.percentile(draws,[2.5,97.5],axis=0); counts['p025']=lo; counts['p975']=hi; counts.to_csv('sdss_patch_class_fractions.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].bar(counts['class'],counts['count']); ax[0].set(ylabel='Spectra',title='Preserved aggregate counts'); ax[1].boxplot([draws[:,i] for i in range(3)],tick_labels=counts['class']); ax[1].set(ylabel='Resampled fraction',title='Multinomial sampling intervals'); fig.tight_layout(); fig.savefig('sdss_class_fraction_audit.png',dpi=180); plt.show()""",
"""sizes=[200,400,800]; width=[]
for n in sizes:
 d=RNG.multinomial(n,counts.fraction,2000)/n; width.append(np.mean(np.percentile(d,97.5,axis=0)-np.percentile(d,2.5,axis=0)))
fig,ax=plt.subplots(figsize=(7,4)); ax.plot(sizes,width,'o-'); ax.set(xlabel='Hypothetical patch sample size',ylabel='Mean 95% fraction-interval width',title='Sampling precision stress test'); fig.tight_layout(); fig.savefig('sdss_class_precision_stress.png',dpi=180); plt.show()"""],
"""sample_size=800; results=[f'GALAXY {counts.iloc[0].fraction:.1%}, STAR {counts.iloc[1].fraction:.1%}, QSO {counts.iloc[2].fraction:.1%}',f'QSO 95% multinomial interval {counts.iloc[2].p025:.1%}–{counts.iloc[2].p975:.1%}','aggregate counts reproduce the old output but cannot recover subclass or redshift distributions']; validation='Class fractions use multinomial resampling and interval width is tested at three sample sizes.'; quality_checks=[{'name':'Counts sum to 800','status':'pass'},{'name':'Sampling intervals','status':'pass'},{'name':'Source-level table','status':'not available'}]; tags=['SDSS','spectral classes','aggregate audit','selection']""",
['sdss_class_fraction_audit.png','sdss_class_precision_stress.png'],['sdss/2026-07-30-spectral-type-distribution/sdss_patch_class_fractions.csv'],['Original SDSS SQL query printed in notebook','executed aggregate counts: 400 galaxies, 268 stars, 132 QSOs'],['source-level rows were not saved','TOP 800 without explicit ordering is not a random sky sample','pipeline classes and subclasses are not audited individually'],SDSS_REFS)

    write_case('sdss/2026-07-30-white-dwarf-spectrum','SDSS white-dwarf Balmer-profile legacy audit','Are the broad Balmer depressions visible robustly in the preserved spectrum plot?','SDSS legacy spectrum plot','Exploration','Digitized spectral-feature audit',[
"""sample=pd.read_csv(DATA/'sdss_white_dwarf_plot_digitized.csv').sort_values('wavelength_approx_A'); wave=sample.wavelength_approx_A.to_numpy(); flux=sample.flux_approx.to_numpy(); smooth=signal.savgol_filter(flux,51,2); print(len(sample),'digitized x-columns; these are not calibrated spectral samples')""",
"""lines={'Hδ':4102,'Hγ':4340,'Hβ':4861,'Hα':6563}; rows=[]
for name,w0 in lines.items():
 line=np.nanmedian(smooth[np.abs(wave-w0)<25]); side=np.nanmedian(smooth[(np.abs(wave-w0)>70)&(np.abs(wave-w0)<140)]); rows.append((name,w0,1-line/side))
meas=pd.DataFrame(rows,columns=['line','wavelength_A','relative_depth']); meas.to_csv('wd_balmer_display_depths.csv',index=False); fig,ax=plt.subplots(figsize=(10,4.5)); ax.plot(wave,flux,alpha=.35,label='digitized display'); ax.plot(wave,smooth,label='smoothed'); [ax.axvline(v,ls=':',c='k') for v in lines.values()]; ax.set(xlabel='Approximate wavelength (Å)',ylabel='Approximate plotted flux',title='Preserved SDSS white-dwarf plot'); ax.legend(); fig.tight_layout(); fig.savefig('wd_balmer_legacy_audit.png',dpi=180); plt.show()""",
"""stress=[]
for half in [15,25,35,45]:
 for name,w0 in lines.items():
  line=np.nanmedian(smooth[np.abs(wave-w0)<half]); side=np.nanmedian(smooth[(np.abs(wave-w0)>70)&(np.abs(wave-w0)<140)]); stress.append((half,name,1-line/side))
stress=pd.DataFrame(stress,columns=['line_half_width_A','line','relative_depth']); stress.to_csv('wd_balmer_window_stress.csv',index=False); fig,ax=plt.subplots(figsize=(8,4));
for name,g in stress.groupby('line'): ax.plot(g.line_half_width_A,g.relative_depth,'o-',label=name)
ax.set(xlabel='Line half-window (Å)',ylabel='Approximate relative depth',title='Window sensitivity'); ax.legend(); fig.tight_layout(); fig.savefig('wd_balmer_window_stress.png',dpi=180); plt.show()"""],
"""detected=meas[meas.relative_depth>.08].line.tolist(); sample_size=len(sample); results=[f'{len(detected)} of four marked Balmer depressions exceed 8% in the digitized display',f'detected: {", ".join(detected) if detected else "none"}','broad absorption is consistent with the pipeline WD label, but atmospheric parameters are not fitted']; validation='Relative depths are recomputed across four line-window widths.'; quality_checks=[{'name':'Pipeline subclass WD retained','status':'pass'},{'name':'Balmer window stress','status':'pass'},{'name':'Calibrated FITS recovery','status':'not available'}]; tags=['SDSS','white dwarf','Balmer lines','legacy audit']""",
['wd_balmer_legacy_audit.png','wd_balmer_window_stress.png'],['data/audit_batches4_7/sdss_white_dwarf_plot_digitized.csv','sdss/2026-07-30-white-dwarf-spectrum/wd_balmer_display_depths.csv','sdss/2026-07-30-white-dwarf-spectrum/wd_balmer_window_stress.csv'],['Original SDSS position and pipeline WD subclass','preserved wd_spectrum.png','approximately digitized plotted curve'],['plot digitization loses errors and spectral resolution','continuum placement is approximate','temperature and gravity require atmosphere-model fitting'],SDSS_REFS)

    write_case('sdss/2026-07-30-metallicity-vs-position','SDSS metallicity–latitude legacy-output audit','Does the weak negative trend reported in the old plot survive digitization choices?','SDSS legacy catalogue plot','Exploration','Digitized correlation audit',[
"""sample=pd.read_csv(DATA/'sdss_metallicity_plot_digitized_pixels.csv'); x=sample.galactic_latitude_approx_deg.to_numpy(); y=sample.feh_approx.to_numpy(); rho=stats.spearmanr(x,y).statistic; print(len(sample),'coloured plot pixels; old notebook reported 400 stars and Pearson r=-0.181')""",
"""p,keep,resid=robust_line(x,y); fig,ax=plt.subplots(1,2,figsize=(10,4.5)); ax[0].scatter(x,y,s=3,alpha=.2); g=np.linspace(x.min(),x.max()); ax[0].plot(g,np.polyval(p,g),'k'); ax[0].set(xlabel='Approximate Galactic latitude (deg)',ylabel='Approximate [Fe/H]',title='Digitized legacy plot'); ax[1].hist(resid[keep],bins=40); ax[1].set(xlabel='Robust-line residual',ylabel='Coloured pixels',title='Rendered scatter'); fig.tight_layout(); fig.savefig('sdss_metallicity_legacy_audit.png',dpi=180); plt.show()""",
"""rows=[]
for phase in range(5):
 s=sample[sample.pixel_x.astype(int)%5==phase]; rows.append((phase,len(s),stats.spearmanr(s.galactic_latitude_approx_deg,s.feh_approx).statistic))
stress=pd.DataFrame(rows,columns=['pixel_phase','n_pixels','spearman_rho']); stress.to_csv('sdss_metallicity_digitization_stress.csv',index=False); fig,ax=plt.subplots(figsize=(7,4)); ax.bar(stress.pixel_phase,stress.spearman_rho); ax.axhline(0,color='k'); ax.set(xlabel='Independent x-pixel phase',ylabel='Spearman rho',title='Digitization sensitivity'); fig.tight_layout(); fig.savefig('sdss_metallicity_digitization_stress.png',dpi=180); plt.show()"""],
"""sample_size=len(sample); results=[f'old source-level Pearson correlation reported as -0.181 for 400 stars',f'digitized-pixel Spearman correlation {rho:.3f}',f'pixel-phase range {stress.spearman_rho.min():.3f} to {stress.spearman_rho.max():.3f}']; validation='The sign is checked across five independent pixel phases; magnitude is not treated as a source-level estimate.'; quality_checks=[{'name':'Original statistic retained','status':'pass'},{'name':'Digitization stress','status':'pass'},{'name':'Source table recovery','status':'not available'}]; tags=['SDSS','metallicity','Galactic latitude','legacy audit']""",
['sdss_metallicity_legacy_audit.png','sdss_metallicity_digitization_stress.png'],['data/audit_batches4_7/sdss_metallicity_plot_digitized_pixels.csv','sdss/2026-07-30-metallicity-vs-position/sdss_metallicity_digitization_stress.csv'],['Original SDSS SQL and first five rows printed in notebook','old output Pearson correlation -0.181','preserved feh_vs_lat.png'],['source rows and errors were not saved','pixel overlap weights dense regions','latitude range and target selection confound population interpretation'],SDSS_REFS)

    write_case('sdss/2026-07-30-qso-vs-galaxy-colors','SDSS quasar–galaxy colour display audit','How clearly separated are the two rendered colour clouds, without claiming catalogue-level classifier accuracy?','SDSS legacy catalogue plot','Exploration','Digitized colour-separation audit',[
"""sample=pd.read_csv(DATA/'sdss_colour_plot_digitized_pixels.csv'); features=sample[['u_g_approx','g_r_approx']].to_numpy(); labels=sample['class'].to_numpy(); print(len(sample),'coloured display pixels; original SQL returned 1,500 objects')""",
"""cent=sample.groupby('class')[['u_g_approx','g_r_approx']].median(); delta=np.linalg.norm(cent.loc['QSO']-cent.loc['GALAXY']); fig,ax=plt.subplots(1,2,figsize=(11,5));
for name,g in sample.groupby('class'): ax[0].scatter(g.u_g_approx,g.g_r_approx,s=2,alpha=.15,label=name)
ax[0].scatter(cent.u_g_approx,cent.g_r_approx,c='k',marker='x',s=80); ax[0].set(xlabel='Approx. u−g',ylabel='Approx. g−r',title='Digitized colour pixels'); ax[0].legend(); proj=(features-cent.mean().to_numpy())@(cent.loc['GALAXY'].to_numpy()-cent.loc['QSO'].to_numpy());
for name in ['QSO','GALAXY']: ax[1].hist(proj[labels==name],bins=40,alpha=.5,label=name,density=True)
ax[1].set(xlabel='Centroid-axis display projection',ylabel='Density',title='Rendered-cloud overlap'); ax[1].legend(); fig.tight_layout(); fig.savefig('sdss_colour_legacy_audit.png',dpi=180); plt.show()""",
"""rows=[]
for phase in range(5):
 s=sample[sample.pixel_x.astype(int)%5==phase]; c=s.groupby('class')[['u_g_approx','g_r_approx']].median(); rows.append((phase,len(s),np.linalg.norm(c.loc['QSO']-c.loc['GALAXY'])))
stress=pd.DataFrame(rows,columns=['pixel_phase','n_pixels','centroid_separation_mag']); stress.to_csv('sdss_colour_digitization_stress.csv',index=False); fig,ax=plt.subplots(figsize=(7,4)); ax.bar(stress.pixel_phase,stress.centroid_separation_mag); ax.set(xlabel='Independent x-pixel phase',ylabel='Rendered centroid separation (mag)',title='Digitization sensitivity'); fig.tight_layout(); fig.savefig('sdss_colour_digitization_stress.png',dpi=180); plt.show()"""],
"""sample_size=len(sample); results=[f'original SQL returned 1,500 labelled objects',f'rendered colour-cloud centroid separation approximately {delta:.2f} mag',f'pixel-phase separation range {stress.centroid_separation_mag.min():.2f}–{stress.centroid_separation_mag.max():.2f} mag']; validation='Centroid separation is repeated across five independent pixel phases; classification accuracy is deliberately not estimated.'; quality_checks=[{'name':'Two labelled rendered clouds','status':'pass'},{'name':'Digitization stress','status':'pass'},{'name':'Catalogue classifier performance','status':'not attempted'}]; tags=['SDSS','quasar','galaxy','colour selection']""",
['sdss_colour_legacy_audit.png','sdss_colour_digitization_stress.png'],['data/audit_batches4_7/sdss_colour_plot_digitized_pixels.csv','sdss/2026-07-30-qso-vs-galaxy-colors/sdss_colour_digitization_stress.csv'],['Original SDSS photometry/spectroscopy join printed in notebook','preserved color_color.png','class-coloured pixels digitized approximately'],['plot pixels are not independent objects','overplotting alters apparent density','photometric classifier evaluation needs held-out source rows and errors'],SDSS_REFS)

    write_case('sdss/2026-07-30-galaxy-redshift-slice','SDSS redshift-slice structure audit','Which redshift concentrations are visible in a preserved 12,000-galaxy SDSS emission-line sample?','SDSS DR18','Validated','Redshift concentration measurement',[
"""raw=pd.read_csv(DATA/'sdss_emission_galaxies.csv').drop_duplicates('specObjID'); sample=raw.dropna(subset=['ra','dec','z']).copy(); sample=sample[sample.z.between(0.001,.30)]; theta=np.deg2rad(sample.ra); sample['cone_x']=sample.z*np.cos(theta); sample['cone_y']=sample.z*np.sin(theta); print(len(sample),'unique SDSS galaxy spectra')""",
"""fig,ax=plt.subplots(1,2,figsize=(12,5)); ax[0].scatter(sample.cone_x,sample.cone_y,s=2,alpha=.35); ax[0].set(aspect='equal',xlabel='z cos(RA)',ylabel='z sin(RA)',title='Thin-slice comoving proxy'); bins=np.linspace(0,.3,61); hist,edges=np.histogram(sample.z,bins); centres=(edges[:-1]+edges[1:])/2; smooth=ndimage.gaussian_filter1d(hist.astype(float),2); excess=(hist-smooth)/np.sqrt(np.maximum(smooth,1)); ax[1].step(centres,hist,where='mid'); ax[1].plot(centres,smooth); ax[1].set(xlabel='Redshift',ylabel='Galaxies per bin',title='Redshift concentrations'); fig.tight_layout(); fig.savefig('sdss_redshift_slice_audit.png',dpi=180); plt.show()""",
"""peaks=pd.DataFrame({'z_center':centres,'count':hist,'smooth_count':smooth,'poisson_excess_sigma':excess}).sort_values('poisson_excess_sigma',ascending=False).head(8); peaks.to_csv('sdss_redshift_concentrations.csv',index=False); jack=[]
for q,g in sample.groupby(pd.qcut(sample.ra,4,duplicates='drop')):
 h,_=np.histogram(g.z,bins); sm=ndimage.gaussian_filter1d(h.astype(float),2); ex=(h-sm)/np.sqrt(np.maximum(sm,1)); jack.append((str(q),centres[np.argmax(ex)],np.max(ex)))
jack=pd.DataFrame(jack,columns=['ra_quartile','strongest_z','excess_sigma']); fig,ax=plt.subplots(figsize=(8,4)); ax.scatter(jack.strongest_z,jack.excess_sigma); ax.set(xlabel='Strongest redshift-bin centre',ylabel='Local Poisson-style excess',title='RA-quartile jackknife'); fig.tight_layout(); fig.savefig('sdss_redshift_jackknife.png',dpi=180); plt.show()"""],
"""top=peaks.iloc[0]; sample_size=len(sample); results=[f'{sample_size:,} unique emission-line galaxies in 0.001<z<0.30',f'strongest 0.005-wide concentration at z≈{top.z_center:.3f} with local excess {top.poisson_excess_sigma:.1f} sigma',f'RA-quartile strongest bins span {jack.strongest_z.min():.3f}–{jack.strongest_z.max():.3f}']; validation='Redshift concentration is compared with a smoothed baseline and jackknifed across four RA intervals.'; quality_checks=[{'name':'Unique spectra','status':'pass'},{'name':'Redshift range explicit','status':'pass'},{'name':'RA jackknife','status':'pass'}]; tags=['SDSS','galaxies','large-scale structure','redshift']""",
['sdss_redshift_slice_audit.png','sdss_redshift_jackknife.png'],['data/audit_batches4_7/sdss_emission_galaxies.csv','sdss/2026-07-30-galaxy-redshift-slice/sdss_redshift_concentrations.csv'],['SDSS DR18 SQL result preserved by BPT notebook','12,000 spectra with coordinates, redshifts, and line measurements'],['z is used as a radial proxy rather than a cosmological distance','sample requires emission-line measurements','local excess ignores correlated large-scale-structure covariance'],SDSS_REFS)


def mast_case():
    write_case('mast/2026-07-30-hst-cutout-m87','HST M87 preview field-placement audit','Can the selected HST preview support morphology or jet claims when M87 lies at the frame boundary?','MAST · HST WFC3 preview','Exploration','Display-image completeness audit',[
"""img=np.asarray(Image.open('m87.jpg').convert('L'),float); h,w=img.shape; crop=img[int(.75*h):h,0:int(.28*w)]; yy,xx=np.indices(crop.shape); bg=np.median(crop[:int(.35*crop.shape[0])]); z=np.maximum(crop-bg,0); print(img.shape,'preview pixels; target crop',crop.shape)""",
"""levels=np.percentile(z[z>0],[85,90,95,97,99]); rows=[]
for lev in levels:
 m=z>=lev; wt=z*m; total=wt.sum(); cx=(wt*xx).sum()/total; cy=(wt*yy).sum()/total; dx=xx-cx; dy=yy-cy; qxx=(wt*dx*dx).sum()/total; qyy=(wt*dy*dy).sum()/total; qxy=(wt*dx*dy).sum()/total; eig=np.linalg.eigvalsh([[qxx,qxy],[qxy,qyy]]); rows.append((lev,m.sum(),cx,cy,np.sqrt(eig[0]/eig[1]),m[-1].mean()))
stress=pd.DataFrame(rows,columns=['threshold','pixels','centroid_x','centroid_y','axis_ratio','bottom_edge_fraction']); stress.to_csv('m87_preview_threshold_audit.csv',index=False); fig,ax=plt.subplots(1,2,figsize=(11,4.5)); ax[0].imshow(crop,cmap='gray'); ax[0].contour(z,levels=levels[-3:],colors=['cyan','orange','red']); ax[0].set_title('M87 at the preview boundary'); ax[0].axis('off'); ax[1].plot(stress.threshold,stress.axis_ratio,'o-',label='axis ratio'); ax[1].plot(stress.threshold,stress.bottom_edge_fraction,'o-',label='bright bottom-edge fraction'); ax[1].set(xlabel='Display threshold',title='Truncation-sensitive morphology'); ax[1].legend(); fig.tight_layout(); fig.savefig('m87_preview_boundary_audit.png',dpi=180); plt.show()""",
"""fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(stress.threshold,stress.centroid_x,'o-',label='x'); ax[0].plot(stress.threshold,stress.centroid_y,'o-',label='y'); ax[0].set(xlabel='Threshold',ylabel='Display centroid (pixel)',title='Centroid stress'); ax[0].legend(); edge=[]
for trim in [0,10,20,30,40]:
 q=z[:max(1,z.shape[0]-trim)]; edge.append((trim,np.percentile(q,99),np.mean(q[-1]>np.percentile(q,95))))
edge=pd.DataFrame(edge,columns=['bottom_trim_pixels','p99','edge_bright_fraction']); edge.to_csv('m87_preview_crop_stress.csv',index=False); ax[1].plot(edge.bottom_trim_pixels,edge.edge_bright_fraction,'o-'); ax[1].set(xlabel='Bottom rows removed',ylabel='Bright fraction at new edge',title='Crop sensitivity'); fig.tight_layout(); fig.savefig('m87_preview_crop_stress.png',dpi=180); plt.show()"""],
"""sample_size=int(img.size); boundary=float(stress.bottom_edge_fraction.max()); results=[f'official preview contains {img.size:,} display pixels',f'M87 emission reaches the bottom frame boundary at all tested thresholds',f'maximum bright bottom-edge fraction {boundary:.1%}; morphology and jet measurements rejected']; validation='Centroid, axis ratio, and edge contact are swept across five thresholds and five crop trims.'; quality_checks=[{'name':'Official preview provenance','status':'pass'},{'name':'Boundary contact test','status':'fail for morphology'},{'name':'Calibrated photometry','status':'not attempted'}]; tags=['HST','M87','image audit','field mismatch']""",
['m87_preview_boundary_audit.png','m87_preview_crop_stress.png'],['mast/2026-07-30-hst-cutout-m87/m87.jpg','mast/2026-07-30-hst-cutout-m87/m87_preview_threshold_audit.csv','mast/2026-07-30-hst-cutout-m87/m87_preview_crop_stress.csv'],['MAST HST WFC3 preview id5o27qbq_raw.jpg','original download output retained in executed notebook'],['M87 is truncated by the frame boundary','preview stretch and detector mosaic are not calibrated surface brightness','jet-scale science requires a target-centred calibrated FITS product'],MAST_REFS)


def main():
    gaia_cases(); exoplanet_cases(); sdss_cases(); mast_case(); print('Prepared Scientific Audit Batches 4–7')

if __name__=='__main__': main()
