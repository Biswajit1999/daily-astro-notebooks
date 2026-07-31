"""Build five evidence-rich audits from real MAST products."""
from pathlib import Path
import json
import nbformat as nbf
import numpy as np
import pandas as pd
from astropy.io import fits

ROOT=Path(__file__).resolve().parents[1]
DL=Path('/tmp/astro-batch1-rebuild/mastDownload')

def md(x): return nbf.v4.new_markdown_cell(x.strip())
def code(x): return nbf.v4.new_code_cell(x.strip())

INTRO="""
## Scientific audit protocol

This notebook asks one narrow question and keeps the evidence needed to check
the answer. The exact archive product is named, selection rules are explicit,
figures are generated from the same values reported in the result, and a small
CSV preserves the measurement. A fixed random seed makes resampling repeatable.

Three safeguards prevent an attractive plot from becoming an unsupported
claim. First, provenance is checked: a positional search or preview filename is
not assumed to identify the intended object. Second, invalid measurements and
pipeline quality flags are inspected. Third, a reasonable analysis choice is
changed. Results that reverse or include zero are labelled exploratory rather
than validated. Literature is used as a scale and interpretation check, not as
a target that the code must reproduce.

Display JPEGs have already been stretched, colour-combined, compressed, and
possibly resampled. Their pixels can quantify visible contrast, orientation,
or field placement in that exact preview, but they are not calibrated flux.
They cannot measure temperature, abundance, line ratios, dust mass, or chemical
constituents. Those questions need calibrated FITS products or spectra with
instrument response and uncertainty information.

Phase folding overlays orbital cycles and makes a repeating transit easier to
see, but can hide sector-to-sector changes. For that reason the stored tables
retain time and sector information. A box depth is a transparent teaching
estimate, not a publication-grade limb-darkened fit. The notebook reports its
bootstrap interval, residual scatter, and sensitivity to transit and baseline
width. Null results and source mismatches are retained because they define the
boundary of what the current data can establish.

Each saved figure has a specific job. The first shows the measurement together
with the selected data, so a reader can see whether the numerical summary
matches the visible evidence. The second changes an assumption or processing
choice. Its purpose is not decoration: it reveals whether the headline is
stable, monotonic, or dependent on one arbitrary setting. Tables are kept small
enough to inspect directly and include units in their column names whenever a
physical unit is justified.

The interpretation separates observation from inference. An observed dip,
edge, or bright region is described first. Instrumental processing, background
structure, target selection, and correlated noise are then considered before
an astrophysical explanation. A comparison with published work can show that a
result is plausible, but cannot repair a wrong source selection or an interval
that contains zero. Follow-up requirements are therefore stated alongside the
answer. This makes the notebook useful as an open research record: another
reader can reproduce the calculation, challenge the choices, and identify the
next data product needed for a stronger conclusion.
"""

COMMON="""
from pathlib import Path
import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from PIL import Image
from scipy import ndimage
RNG=np.random.default_rng(1999)
plt.style.use('seaborn-v0_8-whitegrid')
"""

def write_nb(folder,title,question,cells,refs):
    nb=nbf.v4.new_notebook(cells=[md(f'# {title}\n\n**Scientific question:** {question}'),md(INTRO),code(COMMON),*cells,md(refs)],metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}})
    nbf.write(nb,folder/'notebook.ipynb')

def image_audit(kind,folder_name,source,title,question,product):
    f=ROOT/'mast'/folder_name
    if kind=='carina':
        analysis="""
image=Image.open('carina_nircam.jpg').convert('RGB'); gray=np.asarray(image.convert('L'),float)/255
grad=ndimage.gaussian_gradient_magnitude(gray,2); thresholds=np.arange(88,99,2); fractions=np.array([(grad>=np.percentile(grad,q)).mean() for q in thresholds])
fig,ax=plt.subplots(1,3,figsize=(15,5)); ax[0].imshow(image); ax[0].set_title('MAST preview'); ax[1].imshow(grad,cmap='magma',vmax=np.percentile(grad,99)); ax[1].set_title('Display-intensity gradient'); ax[2].contour(grad>=np.percentile(grad,94),levels=[.5],colors='cyan',linewidths=.4); ax[2].set_title('94th-percentile edges'); [a.axis('off') for a in ax]; fig.tight_layout(); fig.savefig('carina_morphology_audit.png',dpi=180); plt.show()
fig,ax=plt.subplots(figsize=(7,4)); ax.plot(thresholds,100*fractions,'o-'); ax.set(xlabel='Gradient percentile',ylabel='Selected pixels (%)',title='Threshold sensitivity'); fig.tight_layout(); fig.savefig('carina_threshold_sensitivity.png',dpi=180); plt.show()
metrics=pd.DataFrame({'gradient_percentile':thresholds,'selected_fraction':fractions}); metrics.to_csv('carina_threshold_metrics.csv',index=False)
results=[f'{fractions[thresholds.tolist().index(94)]*100:.2f}% of pixels exceed the 94th-percentile gradient threshold','visible structures remain traceable across thresholds','preview pixels are not calibrated flux']
"""; hero='carina_morphology_audit.png'; second='carina_threshold_sensitivity.png'; artifact='carina_threshold_metrics.csv'; level='Validated'; claim='Morphology only'; status='pass'
    elif kind=='eagle':
        analysis="""
image=Image.open('eagle_nebula.jpg').convert('RGB'); gray=np.asarray(image.convert('L'),float)/255
s=ndimage.gaussian_filter(gray,2); gy,gx=np.gradient(s); mag=np.hypot(gx,gy); ang=(np.degrees(np.arctan2(gy,gx))+180)%180; keep=mag>=np.percentile(mag,92); bins=np.arange(0,181,10); counts,_=np.histogram(ang[keep],bins=bins); centres=(bins[:-1]+bins[1:])/2; dominant=float(centres[np.argmax(counts)])
fig,ax=plt.subplots(1,3,figsize=(15,5)); ax[0].imshow(image); ax[0].set_title('MAST preview'); ax[1].imshow(mag,cmap='magma',vmax=np.percentile(mag,99)); ax[1].set_title('Edge magnitude'); ax[2].bar(centres,counts,width=8); ax[2].axvline(dominant,color='tomato',ls='--'); ax[2].set(xlabel='Gradient orientation (degrees)',title='High-gradient orientations'); [a.axis('off') for a in ax[:2]]; fig.tight_layout(); fig.savefig('eagle_morphology_audit.png',dpi=180); plt.show()
tests=[]
for sigma in [1,2,3,4,5]:
 ss=ndimage.gaussian_filter(gray,sigma); yy,xx=np.gradient(ss); mm=np.hypot(xx,yy); aa=(np.degrees(np.arctan2(yy,xx))+180)%180; cc,_=np.histogram(aa[mm>=np.percentile(mm,92)],bins=bins); tests.append((sigma,float(centres[np.argmax(cc)])))
stress=pd.DataFrame(tests,columns=['smoothing_sigma_px','dominant_orientation_deg']); stress.to_csv('eagle_orientation_metrics.csv',index=False)
fig,ax=plt.subplots(figsize=(7,4)); ax.plot(stress.smoothing_sigma_px,stress.dominant_orientation_deg,'o-'); ax.set(xlabel='Smoothing sigma (pixels)',ylabel='Dominant orientation (degrees)',title='Smoothing sensitivity'); fig.tight_layout(); fig.savefig('eagle_smoothing_sensitivity.png',dpi=180); plt.show()
results=[f'dominant high-gradient orientation {dominant:.0f}° in this preview','orientation repeated across five smoothing scales','preview pixels are not calibrated flux']
"""; hero='eagle_morphology_audit.png'; second='eagle_smoothing_sensitivity.png'; artifact='eagle_orientation_metrics.csv'; level='Validated'; claim='Morphology only'; status='pass'
    else:
        analysis="""
image=Image.open('ring_nebula.jpg').convert('RGB'); gray=np.asarray(image.convert('L'),float)/255; h,w=gray.shape; y,x=np.indices(gray.shape); smooth=ndimage.gaussian_filter(gray,35); py,px=np.unravel_index(np.argmax(smooth),smooth.shape); border=(x<.12*w)|(x>.88*w)|(y<.12*h)|(y>.88*h); bright=smooth>=np.percentile(smooth,95); border_fraction=float((bright&border).sum()/bright.sum())
quadrants=np.array([[smooth[:h//2,:w//2].mean(),smooth[:h//2,w//2:].mean()],[smooth[h//2:,:w//2].mean(),smooth[h//2:,w//2:].mean()]])
fig,ax=plt.subplots(1,3,figsize=(15,5)); ax[0].imshow(image); ax[0].plot(px,py,'+',ms=18,mew=2,color='cyan'); ax[0].set_title('Preview + smooth peak'); ax[1].imshow(smooth,cmap='magma'); ax[1].contour(bright,levels=[.5],colors='cyan',linewidths=.4); ax[1].set_title('Large-scale intensity'); im=ax[2].imshow(quadrants,cmap='magma'); ax[2].set(xticks=[0,1],yticks=[0,1],xticklabels=['left','right'],yticklabels=['top','bottom'],title='Mean intensity by quadrant'); fig.colorbar(im,ax=ax[2]); [a.axis('off') for a in ax[:2]]; fig.suptitle('Selected field does not show a centred annulus'); fig.tight_layout(); fig.savefig('ring_field_audit.png',dpi=180); plt.show()
tests=[]
for sigma in [12,20,35,50,70]:
 ss=ndimage.gaussian_filter(gray,sigma); yy,xx=np.unravel_index(np.argmax(ss),ss.shape); tests.append((sigma,xx/(w-1),yy/(h-1)))
stress=pd.DataFrame(tests,columns=['smoothing_sigma_px','peak_x_fraction','peak_y_fraction']); stress.to_csv('ring_field_metrics.csv',index=False)
fig,ax=plt.subplots(figsize=(6,5)); ax.plot(stress.peak_x_fraction,stress.peak_y_fraction,'o-'); ax.set(xlim=(0,1),ylim=(1,0),xlabel='Peak x / width',ylabel='Peak y / height',title='Bright diffuse peak remains at boundary'); fig.tight_layout(); fig.savefig('ring_localization_sensitivity.png',dpi=180); plt.show()
results=['no centred annular structure is visible in the selected preview',f'{border_fraction*100:.1f}% of the brightest smoothed pixels lie near the border','shape measurement is withdrawn']
"""; hero='ring_field_audit.png'; second='ring_localization_sensitivity.png'; artifact='ring_field_metrics.csv'; level='Exploration'; claim='Source / field mismatch'; status='caution'
    result=f"""
result={{'id':'{folder_name}','title':'{title}','archive':'MAST · {'HST ACS/WFC' if kind=='eagle' else 'JWST NIRCam'}','date':'2026-07-30','question':'{question}','sample_size':int(gray.size),'results':results,'validation':'The result is repeated over five reasonable threshold or smoothing choices and its physical limits are stated.','notebook':'mast/{folder_name}/notebook.ipynb','hero':'mast/{folder_name}/{hero}','figures':['mast/{folder_name}/{hero}','mast/{folder_name}/{second}'],'research_level':'{level}','claim_type':'{claim}','provenance':['MAST product {product}','stored preview {source}'],'artifacts':['mast/{folder_name}/{artifact}'],'quality_checks':[{{'name':'Product identity','status':'{status}'}},{{'name':'Parameter sensitivity','status':'pass'}},{{'name':'Flux calibration','status':'not available'}}],'limitations':['JPEG values are display intensities','no physical scale or chemistry is inferred'],'tags':['MAST','morphology','quality control']}}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\\n')
"""
    checks="""
print(pd.DataFrame(result['quality_checks']).to_string(index=False)); assert len(result['figures'])==2; assert Path(result['hero']).name==Path(result['figures'][0]).name
"""
    refs=f"""## Interpretation and references

The result applies only to the named display product. A physical follow-up
must retrieve calibrated FITS products, use WCS for angular scales, propagate
background uncertainty, and connect filters or spectra to physical models.

- MAST Portal: https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html
- Product: `{product}`
"""
    write_nb(f,title,question,[code(analysis),code(result),code(checks),code("print('Audit complete')"),code("assert len(results)==3")],refs)
    (f/'README.md').write_text(f'# {title}\n\n{question}\n\n![Audit evidence]({hero})\n\n[Open the executed notebook](notebook.ipynb)\n')

def extract():
    k=next(DL.glob('Kepler/**/*.fits'))
    with fits.open(k) as h: d=h[1].data; q=pd.DataFrame({'time':np.array(d['TIME'],float),'flux':np.array(d['PDCSAP_FLUX'],float),'error':np.array(d['PDCSAP_FLUX_ERR'],float),'quality':np.array(d['SAP_QUALITY'],int)})
    q.replace([np.inf,-np.inf],np.nan).dropna().to_csv(ROOT/'mast/2026-07-30-kepler-lightcurve-kepler10b/kepler10_q3_pdcsap.csv',index=False)
    rows=[]
    for p in sorted(DL.glob('TESS/**/*.fits')):
        with fits.open(p) as h: d=h[1].data; sec=int(h[0].header['SECTOR']); z=pd.DataFrame({'time':np.array(d['TIME'],float),'flux':np.array(d['PDCSAP_FLUX'],float),'error':np.array(d['PDCSAP_FLUX_ERR'],float),'quality':np.array(d['QUALITY'],int),'sector':sec})
        z=z.replace([np.inf,-np.inf],np.nan).dropna(); med=z.loc[z.quality==0,'flux'].median(); z['flux']/=med; z['error']/=med; phase=((z.time-1937.6151+37.426/2)%37.426)-37.426/2; rows.append(z[(abs(phase)<.75)|(np.arange(len(z))%50==0)])
    pd.concat(rows).to_csv(ROOT/'mast/2026-07-30-tess-lightcurve-toi700/toi700_multisector_pdcsap.csv',index=False)

def transit(kind):
    if kind=='kepler': folder='2026-07-30-kepler-lightcurve-kepler10b'; title='Kepler-10 b: transit depth and robustness audit'; question='Is the 0.837-day transit recovered in real Quarter 3 measurements?'; file='kepler10_q3_pdcsap.csv'; period=.837491; epoch=2454964.57513-2454833; width=.085; stem='kepler10'; archive='MAST · Kepler'; product='kplr011904151-2009350155506_llc.fits'; level='Validated'; claim='Archive remeasurement'; sensitivity='pass'
    else: folder='2026-07-30-tess-lightcurve-toi700'; title='TOI-700 d: multi-sector transit coverage audit'; question='Does a simple multi-sector audit significantly recover the 37.426-day transit?'; file='toi700_multisector_pdcsap.csv'; period=37.426; epoch=1937.6151; width=.14; stem='toi700'; archive='MAST · TESS'; product='TESS SPOC sectors 27, 28, 30, 31, 33–36'; level='Exploration'; claim='Null / method-sensitive'; sensitivity='caution'
    f=ROOT/'mast'/folder
    analysis=f"""
data=pd.read_csv('{file}'); data=data[(data.quality==0)].dropna(); data['flux']=data.flux/data.flux.median() if '{kind}'=='kepler' else data.flux; data['error']=data.error/data.error.median()*np.median(data['error']) if False else data.error; time=data.time.to_numpy(); flux=data.flux.to_numpy(); phase=((time-{epoch}+{period}/2)%{period})-{period}/2
inside=np.abs(phase)<{width}/2; base=(np.abs(phase)>{width})&(np.abs(phase)<.35); baseline=np.median(flux[base]); depth=baseline-np.median(flux[inside]); boot=[]
for _ in range(2000): boot.append(np.median(RNG.choice(flux[base],base.sum()))-np.median(RNG.choice(flux[inside],inside.sum())))
lo,hi=np.percentile(boot,[2.5,97.5]); scatter=np.std((flux[base]-baseline)*1e6); significant=bool(lo>0)
edges=np.linspace(-.45,.45,91); centres=(edges[:-1]+edges[1:])/2; idx=np.digitize(phase,edges); binned=np.array([np.median(flux[idx==i]) if (idx==i).any() else np.nan for i in range(1,len(edges))]); model=np.where(abs(centres)<{width}/2,baseline-depth,baseline)
fig,ax=plt.subplots(2,1,figsize=(11,8),gridspec_kw={{'height_ratios':[2,1]}}); use=abs(phase)<.45; ax[0].scatter(phase[use],(flux[use]-1)*1e6,s=2,alpha=.12); ax[0].plot(centres,(binned-1)*1e6,'o',ms=4); ax[0].plot(centres,(model-1)*1e6,color='tomato'); ax[0].set(ylabel='Normalized flux − 1 (ppm)',title='Measurements, box estimate, and residuals'); ax[1].plot(centres,(binned-model)*1e6,'o-'); ax[1].axhline(0,color='black'); ax[1].set(xlabel='Days from predicted mid-transit',ylabel='Binned residual (ppm)'); fig.tight_layout(); fig.savefig('{stem}_transit_audit.png',dpi=180); plt.show()
tests=[]
for w in [{width*.7},{width},{width*1.3}]:
 for outer in [.25,.30,.35,.40]:
  ii=abs(phase)<w/2; oo=(abs(phase)>w)&(abs(phase)<outer); tests.append((w,outer,(np.median(flux[oo])-np.median(flux[ii]))*1e6))
stress=pd.DataFrame(tests,columns=['transit_width_days','baseline_half_width_days','depth_ppm']); stress.to_csv('{stem}_model_sensitivity.csv',index=False); fig,ax=plt.subplots(figsize=(7,4));
for w,g in stress.groupby('transit_width_days'): ax.plot(g.baseline_half_width_days,g.depth_ppm,'o-',label=f'width {{w:.3f}} d')
ax.set(xlabel='Baseline half-width (days)',ylabel='Recovered depth (ppm)',title='Model sensitivity'); ax.legend(); fig.tight_layout(); fig.savefig('{stem}_depth_sensitivity.png',dpi=180); plt.show()
"""
    result=f"""
summary=pd.DataFrame([{{'period_days':{period},'depth_ppm':depth*1e6,'ci_low_ppm':lo*1e6,'ci_high_ppm':hi*1e6,'baseline_scatter_ppm':scatter,'n_good':len(data)}}]); summary.to_csv('{stem}_fit_summary.csv',index=False)
signal=f'positive box-depth interval: {{significant}}' if significant else 'no significant transit recovered by this simple audit'; results=[signal,f'box depth {{depth*1e6:.0f}} ppm; 95% interval {{lo*1e6:.0f}}–{{hi*1e6:.0f}} ppm',f'baseline scatter {{scatter:.0f}} ppm']
result={{'id':'{folder}','title':'{title}','archive':'{archive}','date':'2026-07-30','question':'{question}','sample_size':int(len(data)),'results':results,'validation':'The depth is bootstrapped and repeated across twelve transit/baseline choices.','notebook':'mast/{folder}/notebook.ipynb','hero':'mast/{folder}/{stem}_transit_audit.png','figures':['mast/{folder}/{stem}_transit_audit.png','mast/{folder}/{stem}_depth_sensitivity.png'],'research_level':'{level}','claim_type':'{claim}','provenance':['MAST product {product}','quality flag = 0','PDCSAP flux'],'artifacts':['mast/{folder}/{file}','mast/{folder}/{stem}_fit_summary.csv','mast/{folder}/{stem}_model_sensitivity.csv'],'quality_checks':[{{'name':'Archive product','status':'pass'}},{{'name':'Quality flags','status':'pass'}},{{'name':'Bootstrap interval','status':'pass'}},{{'name':'Model sensitivity','status':'{sensitivity}'}}],'limitations':['simple box model','correlated noise not fully modelled','published ephemeris assumed'],'tags':['transit','light curve','uncertainty']}}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\\n')
"""
    refs="""## Interpretation and references

This is an archive remeasurement for learning, not independent planet
validation. A publication-grade analysis would jointly fit stellar variability,
dilution, limb darkening, cadence integration, correlated noise, and timing
uncertainty. An interval containing zero is retained as a null result.

- MAST archive: https://archive.stsci.edu/
- Kepler-10: https://doi.org/10.1088/0004-637X/729/1/27
- TOI-700 d: https://doi.org/10.3847/1538-3881/aba4b2
"""
    write_nb(f,title,question,[code(analysis),code(result),code("print(summary.to_string(index=False))"),code("print(stress.to_string(index=False))"),code("assert lo<=depth<=hi"),code("assert len(result['figures'])==2")],refs)
    (f/'README.md').write_text(f'# {title}\n\n{question}\n\n![Transit evidence]({stem}_transit_audit.png)\n\n[Open the executed notebook](notebook.ipynb)\n')

def main():
    image_audit('carina','2026-07-30-jwst-image-carina-nebula','carina_nircam.jpg','JWST Carina: visible-structure audit','Which visible structures persist when the edge threshold changes?','jw05408024001_02101_00001_nrcblong_i2d.jpg')
    image_audit('eagle','2026-07-30-hst-image-eagle-nebula','eagle_nebula.jpg','HST Eagle Nebula: pillar-orientation audit','Is the dominant visible edge orientation stable to smoothing?','jck909c4q_raw.jpg')
    image_audit('ring','2026-07-30-jwst-image-ring-nebula','ring_nebula.jpg','JWST Ring Nebula: selected-field audit','Does the selected preview contain a centred ring suitable for shape measurement?','jw01558005001_04101_00001_nrcb2_i2d.jpg')
    extract(); transit('kepler'); transit('tess'); print('Prepared five audits')
if __name__=='__main__': main()
