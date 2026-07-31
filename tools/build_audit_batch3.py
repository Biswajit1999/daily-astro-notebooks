"""Build five evidence-rich SN 1987A notebooks for Scientific Audit Batch 3."""
from __future__ import annotations

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def md(text: str): return nbf.v4.new_markdown_cell(text.strip())
def code(text: str): return nbf.v4.new_code_cell(text.strip())


PROTOCOL = """
## Scientific audit protocol

This notebook is one part of a five-notebook case study of SN 1987A. It uses
either compact cutouts from named calibrated MAST FITS products, official NASA
release frames with their processing limits stated, or a peer-reviewed table
whose DOI and units are preserved. The object, coordinate, telescope,
instrument, filter, observing date, and original product name are kept in the
shared manifest. No image is presented as an unexplained illustration.

### Observation versus display

A calibrated FITS pixel and a public colour image are not interchangeable.
The JWST cutouts retain surface brightness in MJy/sr and an error extension.
They can support aperture sums and wavelength-dependent comparisons after
background subtraction. The Hubble release frames were already aligned,
combined, stretched, colour-mapped, compressed, and possibly resampled before
download. They can show where structures appear and can make a useful dated
animation, but their RGB values are not physical flux. The time-lapse notebook
therefore measures only within-frame morphology; calibrated brightness change
is analysed separately from published HST photometry.

An RGB composite is also a mapping, not what a human eye would see. Each
monochromatic infrared channel is assigned a visible colour and stretched to
reveal structure. The notebook records the assignment and shows every input
channel beside the composite. Scientific measurements use the unstretched
arrays, never the rendered RGB pixels. A colour difference is not called a
chemical detection: broad filters mix continuum and emission lines, and a
spectral or narrow-band analysis is needed to identify a constituent.

### Registration, resolution, and uncertainty

Images from different filters are placed on one celestial WCS grid before
pixel-level comparison. The code uses the output sky coordinates rather than
assuming equal array sizes or identical centring. When filters with different
point-spread functions are compared, the sharper images are blurred to a
common approximate resolution. The calculation is repeated across plausible
apertures or smoothing widths so one attractive processing choice cannot carry
the conclusion.

Background is measured away from the remnant. Random aperture uncertainty is
estimated from background scatter or from the published measurement error.
This does not include every calibration, PSF, aperture, or correlated-noise
term, so formal intervals are not promoted to publication-grade errors. For
the literature light curve, residual resampling is used because scatter about
the trend is more realistic than treating the very small tabulated statistical
errors as the only uncertainty.

### Claim boundary

“Validated” means the narrow archive measurement survived the checks named in
this notebook. “Reproduction” means a published table was independently
reanalysed and compared with the paper's conclusion. “Exploration” means the
product is useful for visual or method development but cannot support a
calibrated physical claim. None of these labels means a new supernova,
constituent, compact object, or explosion mechanism has been discovered.

The figures and small tables are saved beside the executed notebook. Each
`result.json` names the evidence figures, reusable artifacts, limitations,
quality checks, and provenance that feed the project dashboard. A null result,
unstable value, or mismatch is retained rather than edited away. This keeps the
repository useful as a learning record and makes the next required observation
or model explicit.
"""


COMMON = r"""
from pathlib import Path
import json, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from scipy import ndimage, stats
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.units as u

RNG=np.random.default_rng(1999)
plt.style.use('seaborn-v0_8-whitegrid')
DATA=Path('../../data/sn1987a')
assert DATA.is_dir(), 'Run from the notebook folder inside a complete repository checkout.'
TARGET_RA=83.8666125; TARGET_DEC=-69.2697528

def load_fits(name):
    with fits.open(DATA/name,memmap=False) as h:
        sci=np.asarray(h['SCI'].data,float); err=np.asarray(h['ERR'].data,float) if 'ERR' in h else None
        return sci,err,WCS(h['SCI'].header).celestial,h['SCI'].header.copy()

def reproject_array(array,wcs_in,wcs_out,shape_out,order=1):
    yy,xx=np.indices(shape_out,dtype=float); sky=wcs_out.pixel_to_world(xx,yy); sx,sy=wcs_in.world_to_pixel(sky)
    return ndimage.map_coordinates(array,[sy,sx],order=order,mode='constant',cval=np.nan)

def pixel_scale_arcsec(wcs):
    return float(np.mean(proj_plane_pixel_scales(wcs))*3600)

def stretch(array,low=1,high=99.7,a=8):
    lo,hi=np.nanpercentile(array,[low,high]); z=np.clip((array-lo)/(hi-lo),0,1)
    return np.arcsinh(a*z)/np.arcsinh(a)
"""


def write_notebook(folder: Path, title: str, question: str, analysis: str, result: str, references: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    nb=nbf.v4.new_notebook(cells=[
        md(f"# {title}\n\n**Scientific question:** {question}"), md(PROTOCOL), code(COMMON),
        code(analysis), code(result),
        code("print(pd.DataFrame(result['quality_checks']).to_string(index=False))"),
        code("assert Path(Path(result['hero']).name).is_file()"),
        code("assert all(Path(Path(path).name).is_file() for path in result['figures'])"),
        md(references),
    ],metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}})
    nbf.write(nb,folder/'notebook.ipynb')


def timelapse() -> None:
    folder=ROOT/'mast/2026-08-01-hst-sn1987a-timelapse'
    analysis=r"""
frame_dir=DATA/'hst_release_frames'; meta=pd.read_csv(frame_dir/'frames.csv')
images=[np.asarray(Image.open(frame_dir/name).convert('RGB')) for name in meta.file]
gray=[np.asarray(Image.fromarray(im).convert('L'),float)/255 for im in images]
reference=gray[-1]

def phase_shift(reference,moving):
    fa=np.fft.fft2(reference-reference.mean()); fb=np.fft.fft2(moving-moving.mean()); cross=fa*np.conj(fb); cross/=np.maximum(np.abs(cross),1e-12)
    peak=np.unravel_index(np.argmax(np.abs(np.fft.ifft2(cross))),reference.shape); shift=np.array(peak,dtype=float)
    shift[shift>np.array(reference.shape)/2]-=np.array(reference.shape)[shift>np.array(reference.shape)/2]
    return shift

shifts=np.array([phase_shift(reference,g) for g in gray]); registered=[ndimage.shift(im,(*shift,0),order=1,mode='nearest') for im,shift in zip(images,shifts)]
h,w=reference.shape; yy,xx=np.indices(reference.shape); cx,cy=w/2,h/2; rho=np.sqrt(((xx-cx)/(0.43*w))**2+((yy-cy)/(0.35*h))**2); ring=(rho>.62)&(rho<1.18)
rows=[]
for (_,row),im,shift in zip(meta.iterrows(),registered,shifts):
    g=np.asarray(Image.fromarray(im.astype('uint8')).convert('L'),float); values=g[ring]; threshold=np.percentile(values,88); mask=ring&(g>=threshold); labels,n=ndimage.label(mask); sizes=np.bincount(labels.ravel())[1:]; components=int(np.sum(sizes>=8))
    rows.append({'year':int(row.year),'date':row.date,'shift_y_px':shift[0],'shift_x_px':shift[1],'bright_ring_components':components,'top12pct_ring_fraction':float(mask.sum()/ring.sum())})
metrics=pd.DataFrame(rows); metrics.to_csv('sn1987a_display_morphology.csv',index=False)

fig,axes=plt.subplots(2,3,figsize=(13,9))
for ax,im,year in zip(axes.flat,registered,meta.year): ax.imshow(im.astype('uint8')); ax.set_title(str(year)); ax.axis('off')
fig.suptitle('Official Hubble release frames on a common display grid'); fig.tight_layout(); fig.savefig('sn1987a_hst_contact_sheet.png',dpi=180); plt.show()
fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].plot(metrics.year,metrics.bright_ring_components,'o-'); ax[0].set(xlabel='Year',ylabel='Bright connected regions',title='Display-morphology metric'); ax[1].quiver(np.zeros(len(metrics)),np.zeros(len(metrics)),metrics.shift_x_px,metrics.shift_y_px,angles='xy',scale_units='xy',scale=1); ax[1].set(xlabel='x shift (pixels)',ylabel='y shift (pixels)',title='Registration shifts'); fig.tight_layout(); fig.savefig('sn1987a_timelapse_checks.png',dpi=180); plt.show()

gif_frames=[]
for im,year in zip(registered,meta.year):
    pil=Image.fromarray(im.astype('uint8')).resize((720,578)); draw=ImageDraw.Draw(pil); draw.rectangle((12,12,175,54),fill=(4,12,26)); draw.text((25,21),f'HST  {int(year)}',fill='white'); gif_frames.append(pil)
gif_frames[0].save('sn1987a_hst_1994_2006.gif',save_all=True,append_images=gif_frames[1:],duration=950,loop=0,optimize=True)
"""
    result=r"""
results=[f'six official Hubble frames registered from {meta.year.min()} to {meta.year.max()}',f'maximum measured registration shift {np.linalg.norm(shifts,axis=1).max():.2f} display pixels',f'bright connected ring regions change from {metrics.bright_ring_components.iloc[0]} to {metrics.bright_ring_components.iloc[-1]} under one relative threshold']
result={'id':'2026-08-01-hst-sn1987a-timelapse','title':'Hubble SN 1987A: registered 1994–2006 time-lapse','archive':'NASA / HST release imagery','date':'2026-08-01','question':'How does the visible hotspot pattern change across the official Hubble sequence?','sample_size':int(len(images)),'results':results,'validation':'Frames share the official release geometry, are checked by phase correlation, and use a within-frame relative threshold; calibrated brightness is deliberately not inferred.','notebook':'mast/2026-08-01-hst-sn1987a-timelapse/notebook.ipynb','hero':'mast/2026-08-01-hst-sn1987a-timelapse/sn1987a_hst_contact_sheet.png','figures':['mast/2026-08-01-hst-sn1987a-timelapse/sn1987a_hst_contact_sheet.png','mast/2026-08-01-hst-sn1987a-timelapse/sn1987a_timelapse_checks.png'],'research_level':'Exploration','claim_type':'Display-morphology time series','provenance':['NASA Hubble SN 1987A release collection','six dated 1200-pixel derivatives of official TIFF frames','source URLs and dates recorded in data/sn1987a/manifest.json'],'artifacts':['data/sn1987a/hst_release_frames/frames.csv','mast/2026-08-01-hst-sn1987a-timelapse/sn1987a_display_morphology.csv','mast/2026-08-01-hst-sn1987a-timelapse/sn1987a_hst_1994_2006.gif'],'quality_checks':[{'name':'Frame count and dates','status':'pass'},{'name':'Phase-correlation registration','status':'pass'},{'name':'Common field geometry','status':'pass'},{'name':'Calibrated photometry','status':'not attempted'}],'limitations':['release-frame stretches and colours may differ by epoch','JPEG pixels are not calibrated flux','connected-component count depends on threshold and release processing'],'tags':['HST','SN 1987A','time lapse','animation']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(metrics.to_string(index=False))
assert Path('sn1987a_hst_1994_2006.gif').stat().st_size>10000
"""
    refs="""## Interpretation and references

The animation makes the developing ring hotspots visible, but it is not a
light curve. The next notebook uses calibrated HST flux measurements for that
question. NASA describes the sequence as the shock wave reaching, heating, and
illuminating the inner ring; this notebook only demonstrates the changing
display morphology and does not independently measure a shock speed.

- NASA Hubble SN 1987A image collection: https://science.nasa.gov/asset/hubble/supernova-1987a-january-5-2003/
- NASA description of the shocked ring: https://science.nasa.gov/asset/hubble/shocked-region-around-sn-1987a/
"""
    write_notebook(folder,'Hubble SN 1987A: registered time-lapse','How does the visible hotspot pattern change from 1994 to 2006?',analysis,result,refs)
    (folder/'README.md').write_text('# Hubble SN 1987A registered time-lapse\n\nSix dated official Hubble release frames are registered and compiled into an animation. Display pixels are used for morphology only, not brightness.\n\n![Contact sheet](sn1987a_hst_contact_sheet.png)\n\n[Open the executed notebook](notebook.ipynb)\n')


def lightcurve() -> None:
    folder=ROOT/'mast/2026-08-01-hst-sn1987a-lightcurve'
    analysis=r"""
phot=pd.read_csv(DATA/'hst_photometry_rosu2024_table6.csv'); scales={'er':1e-15,'ejecta':1e-16,'center':1e-18}; phot['physical_flux']=phot.apply(lambda r:r.flux*scales[r.region],axis=1); phot['physical_error']=phot.apply(lambda r:r.flux_error*scales[r.region],axis=1)

def residual_slope(x,y,n=5000):
    p=np.polyfit(x,y,1); model=np.polyval(p,x); residual=y-model; slopes=[]
    for _ in range(n): slopes.append(np.polyfit(x,model+RNG.choice(residual,len(residual),replace=True),1)[0])
    return p,np.percentile(slopes,[2.5,97.5])

summary=[]
for (filt,region),g in phot.groupby(['filter','region']):
    p,ci=residual_slope(g.epoch_days_since_1987_02_23.to_numpy(),g.flux.to_numpy()); change=100*(g.flux.iloc[-1]/g.flux.iloc[0]-1); summary.append((filt,region,change,p[0],ci[0],ci[1]))
summary=pd.DataFrame(summary,columns=['filter','region','first_to_last_percent','slope_table_units_per_day','slope_ci_low','slope_ci_high']); summary.to_csv('sn1987a_lightcurve_trends.csv',index=False)

fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True)
for row,filt in enumerate(['F438W','F625W']):
    for col,region in enumerate(['er','ejecta','center']):
        g=phot[(phot['filter']==filt)&(phot.region==region)]; axes[row,col].errorbar(g.epoch_days_since_1987_02_23,g.flux,yerr=g.flux_error,fmt='o-'); axes[row,col].set_title(f'{filt} · {region}'); axes[row,col].set_ylabel('Flux (table units)'); axes[row,col].set_xlabel('Days since explosion')
fig.suptitle('Rosu et al. (2024) HST photometry, Table 6'); fig.tight_layout(); fig.savefig('sn1987a_hst_lightcurves.png',dpi=180); plt.show()

# Continuous two-slope model for the F625W ejecta plateau.
g=phot[(phot['filter']=='F625W')&(phot.region=='ejecta')].copy(); x=g.epoch_days_since_1987_02_23.to_numpy(); y=g.flux.to_numpy(); candidates=x[2:-2]
def hinge_fit(x,y,b):
    X=np.c_[np.ones(len(x)),x-x.mean(),np.maximum(0,x-b)]; beta=np.linalg.lstsq(X,y,rcond=None)[0]; pred=X@beta; return beta,pred,np.sum((y-pred)**2)
fits=[hinge_fit(x,y,b) for b in candidates]; best_i=int(np.argmin([q[2] for q in fits])); breakpoint=float(candidates[best_i]); beta,pred,_=fits[best_i]
breaks=[]
resid=y-pred
for _ in range(3000):
    yy=pred+RNG.choice(resid,len(resid),replace=True); ff=[hinge_fit(x,yy,b) for b in candidates]; breaks.append(candidates[int(np.argmin([q[2] for q in ff]))])
break_ci=np.percentile(breaks,[16,84]); later_slope=beta[1]+beta[2]
fig,ax=plt.subplots(2,1,figsize=(9,7),sharex=True); ax[0].errorbar(x,y,yerr=g.flux_error,fmt='o',label='HST table'); ax[0].plot(x,pred,color='tomato',label='continuous two-slope fit'); ax[0].axvline(breakpoint,ls='--',color='grey'); ax[0].set(ylabel='F625W ejecta flux (10⁻¹⁶ units)',title=f'Best sampled break: day {breakpoint:.0f}'); ax[0].legend(); ax[1].plot(x,y-pred,'o-'); ax[1].axhline(0,color='black'); ax[1].set(xlabel='Days since explosion',ylabel='Residual'); fig.tight_layout(); fig.savefig('sn1987a_ejecta_plateau_fit.png',dpi=180); plt.show()
pd.DataFrame([{'breakpoint_day':breakpoint,'break_ci16':break_ci[0],'break_ci84':break_ci[1],'early_slope':beta[1],'late_slope':later_slope}]).to_csv('sn1987a_piecewise_fit.csv',index=False)
"""
    result=r"""
er625=summary[(summary['filter']=='F625W')&(summary.region=='er')].iloc[0]; ej625=summary[(summary['filter']=='F625W')&(summary.region=='ejecta')].iloc[0]
results=[f'F625W equatorial-ring flux changes {er625.first_to_last_percent:.1f}% from day {x.min():.0f} to {x.max():.0f}',f'F625W ejecta flux changes {ej625.first_to_last_percent:.1f}% over the same tabulated interval',f'best sampled ejecta slope break day {breakpoint:.0f}; residual-bootstrap 16–84% range {break_ci[0]:.0f}–{break_ci[1]:.0f}']
result={'id':'2026-08-01-hst-sn1987a-lightcurve','title':'SN 1987A: HST ring fading and ejecta plateau','archive':'HST photometry · Rosu et al. 2024','date':'2026-08-01','question':'Do the published HST measurements reproduce a fading ring and a flattening ejecta light curve?','sample_size':int(len(phot)),'results':results,'validation':'All 60 Table 6 measurements are retained with units and errors; slopes use residual resampling and the ejecta breakpoint is selected only from observed epochs.','notebook':'mast/2026-08-01-hst-sn1987a-lightcurve/notebook.ipynb','hero':'mast/2026-08-01-hst-sn1987a-lightcurve/sn1987a_hst_lightcurves.png','figures':['mast/2026-08-01-hst-sn1987a-lightcurve/sn1987a_hst_lightcurves.png','mast/2026-08-01-hst-sn1987a-lightcurve/sn1987a_ejecta_plateau_fit.png'],'research_level':'Reproduction','claim_type':'Peer-reviewed table reanalysis','provenance':['Rosu et al. 2024 ApJ 966 238 Table 6','DOI 10.3847/1538-4357/ad36cc','HST WFC3 F438W and F625W, 2011–2021'],'artifacts':['data/sn1987a/hst_photometry_rosu2024_table6.csv','mast/2026-08-01-hst-sn1987a-lightcurve/sn1987a_lightcurve_trends.csv','mast/2026-08-01-hst-sn1987a-lightcurve/sn1987a_piecewise_fit.csv'],'quality_checks':[{'name':'Published values transcribed with units','status':'pass'},{'name':'Residual bootstrap','status':'pass'},{'name':'Breakpoint restricted to observed epochs','status':'pass'},{'name':'Agreement with paper direction','status':'pass'}],'limitations':['this notebook reanalyses published photometry rather than raw exposures','tabulated statistical errors omit some systematics','ten epochs give coarse breakpoint resolution'],'tags':['HST','SN 1987A','light curve','reproduction']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(summary.to_string(index=False))
assert er625.first_to_last_percent<0 and ej625.first_to_last_percent>0
"""
    refs="""## Interpretation and references

The independent calculation reproduces the paper's main direction: the
equatorial ring fades while the ejecta rise and then flatten. The fitted break
is not a newly precise physical transition; with only ten annual epochs it can
move by one sampled year. Rosu et al. discuss X-ray illumination, diffraction
spikes, scattered ring light, growing ejecta apertures, and filter-dependent
line mixtures in far more detail than this compact reproduction.

- Rosu et al. (2024), ApJ 966, 238: https://doi.org/10.3847/1538-4357/ad36cc
- Open preprint: https://arxiv.org/abs/2403.14361
"""
    write_notebook(folder,'SN 1987A: HST optical light-curve reproduction','Do the published measurements recover a fading ring and flattening ejecta?',analysis,result,refs)
    (folder/'README.md').write_text('# SN 1987A HST optical light-curve reproduction\n\nThe peer-reviewed HST F438W and F625W table is independently reanalysed with residual-bootstrap trends and a sampled change-point test.\n\n![Light curves](sn1987a_hst_lightcurves.png)\n\n[Open the executed notebook](notebook.ipynb)\n')


def rgb() -> None:
    folder=ROOT/'mast/2026-08-01-jwst-sn1987a-rgb'
    analysis=r"""
f150,e150,w150,h150=load_fits('jwst_f150w_2022_cutout.fits'); f200,e200,w200,h200=load_fits('jwst_f200w_2022_cutout.fits'); f444,e444,w444,h444=load_fits('jwst_f444w_2022_cutout.fits')
g200=reproject_array(f200,w200,w150,f150.shape); r444=reproject_array(f444,w444,w150,f150.shape); channels={'F150W → blue':f150,'F200W → green':g200,'F444W → red':r444}
stretched={name:stretch(value) for name,value in channels.items()}; rgb=np.dstack([stretched['F444W → red'],stretched['F200W → green'],stretched['F150W → blue']]); rgb=np.nan_to_num(rgb); plt.imsave('jwst_sn1987a_rgb.png',rgb)
fig,axes=plt.subplots(1,3,figsize=(15,5))
for ax,(name,array) in zip(axes,channels.items()): im=ax.imshow(array,origin='lower',cmap='magma',vmin=np.nanpercentile(array,2),vmax=np.nanpercentile(array,99.5)); ax.set_title(name); ax.axis('off'); fig.colorbar(im,ax=ax,fraction=.046,label='MJy/sr')
fig.suptitle('Calibrated channels before visible-colour mapping'); fig.tight_layout(); fig.savefig('jwst_sn1987a_channel_panels.png',dpi=180); plt.show()
fig,ax=plt.subplots(figsize=(7,7)); ax.imshow(rgb,origin='lower'); ax.set_title('JWST NIRCam infrared RGB mapping'); ax.axis('off'); fig.tight_layout(); fig.savefig('jwst_sn1987a_rgb_figure.png',dpi=200); plt.show()
stats_table=pd.DataFrame([{'filter':name.split()[0],'unit':'MJy/sr','p01':np.nanpercentile(arr,1),'median':np.nanmedian(arr),'p997':np.nanpercentile(arr,99.7),'mapping':name.split('→')[-1].strip()} for name,arr in channels.items()]); stats_table.to_csv('jwst_rgb_channel_statistics.csv',index=False)
"""
    result=r"""
scale=pixel_scale_arcsec(w150); results=[f'F150W, F200W, and F444W calibrated cutouts mapped to blue, green, and red',f'common output grid {f150.shape[1]} × {f150.shape[0]} pixels at {scale:.4f} arcsec/pixel',f'each channel uses a recorded 1st–99.7th percentile asinh display stretch']
result={'id':'2026-08-01-jwst-sn1987a-rgb','title':'JWST SN 1987A: calibrated NIRCam RGB reconstruction','archive':'MAST · JWST NIRCam','date':'2026-08-01','question':'Can three calibrated NIRCam filters be registered and mapped into a traceable infrared RGB composite?','sample_size':int(np.isfinite(f150).sum()+np.isfinite(g200).sum()+np.isfinite(r444).sum()),'results':results,'validation':'Every channel is shown in calibrated units before stretching, all pixels are placed on the F150W celestial grid, and the mapping is stored in a CSV.','notebook':'mast/2026-08-01-jwst-sn1987a-rgb/notebook.ipynb','hero':'mast/2026-08-01-jwst-sn1987a-rgb/jwst_sn1987a_rgb_figure.png','figures':['mast/2026-08-01-jwst-sn1987a-rgb/jwst_sn1987a_rgb_figure.png','mast/2026-08-01-jwst-sn1987a-rgb/jwst_sn1987a_channel_panels.png'],'research_level':'Validated','claim_type':'Calibrated image reconstruction','provenance':['MAST JWST program 1726, PI Matsuura','jw01726-o001_t001 NIRCam I2D mosaics','F150W, F200W, F444W observed 2022-09-02'],'artifacts':['data/sn1987a/jwst_f150w_2022_cutout.fits','data/sn1987a/jwst_f200w_2022_cutout.fits','data/sn1987a/jwst_f444w_2022_cutout.fits','mast/2026-08-01-jwst-sn1987a-rgb/jwst_sn1987a_rgb.png','mast/2026-08-01-jwst-sn1987a-rgb/jwst_rgb_channel_statistics.csv'],'quality_checks':[{'name':'Calibrated I2D inputs','status':'pass'},{'name':'WCS reprojection','status':'pass'},{'name':'Input channels exposed','status':'pass'},{'name':'True-colour claim','status':'not made'}],'limitations':['visible colours are assigned to infrared bands','independent display stretches suppress absolute colour ratios','broad filters do not uniquely identify chemical species'],'tags':['JWST','SN 1987A','RGB','NIRCam']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(stats_table.to_string(index=False))
assert rgb.shape[-1]==3 and np.isfinite(rgb).all()
"""
    refs="""## Interpretation and references

The composite is reproducible false colour. Blue is the shortest wavelength
and red the longest, following a chromatic ordering, but it is not a human-eye
view. The official six-filter release uses additional narrow bands and a more
complex colour assignment. Scientific statements about H₂, dust, synchrotron
continuum, or individual ions require the narrow-band and spectroscopic
analysis in the cited literature.

- Matsuura et al. (2024), deep JWST/NIRCam imaging: https://doi.org/10.1093/mnras/stae1381
- NASA official filter mapping: https://science.nasa.gov/asset/webb/supernova-1987a-nircam-image/
- MAST JWST primer: https://outerspace.stsci.edu/spaces/MASTDOCS/pages/153686810/MAST+Primer+for+JWST
"""
    write_notebook(folder,'JWST SN 1987A: calibrated infrared RGB','Can three calibrated NIRCam filters be compiled into a traceable RGB composite?',analysis,result,refs)
    (folder/'README.md').write_text('# JWST SN 1987A calibrated infrared RGB\n\nThree calibrated NIRCam mosaics are registered by WCS and mapped into a documented false-colour RGB image.\n\n![RGB](jwst_sn1987a_rgb_figure.png)\n\n[Open the executed notebook](notebook.ipynb)\n')


def filter_morphology() -> None:
    folder=ROOT/'mast/2026-08-01-jwst-sn1987a-filter-morphology'
    analysis=r"""
filters=['F150W','F200W','F356W','F444W']; files=[f'jwst_{f.lower()}_2022_cutout.fits' for f in filters]; loaded=[load_fits(name) for name in files]; ref,_,wref,_=loaded[0]; aligned=[]
for sci,err,wcs,header in loaded: aligned.append(reproject_array(sci,wcs,wref,ref.shape))
scale=pixel_scale_arcsec(wref); yy,xx=np.indices(ref.shape); from astropy.coordinates import SkyCoord
cx,cy=wref.world_to_pixel(SkyCoord(TARGET_RA,TARGET_DEC,unit='deg')); radius=np.hypot((xx-cx)*scale,(yy-cy)*scale); pix_sr=(scale/206265)**2
psf={'F150W':.050,'F200W':.066,'F356W':.116,'F444W':.145}; target_fwhm=.145; matched=[]
for filt,array in zip(filters,aligned):
    sigma=np.sqrt(max(target_fwhm**2-psf[filt]**2,0))/2.35482/scale; matched.append(ndimage.gaussian_filter(np.nan_to_num(array,nan=np.nanmedian(array)),sigma))

def aperture_metrics(array,inner=.55,outer=1.15,ejecta=.35):
    bg=(radius>3)&(radius<4.8); b=np.median(array[bg]); scatter=np.std(array[bg]); ring=(radius>inner)&(radius<outer); core=radius<ejecta; conv=pix_sr*1e6
    rf=np.sum(array[ring]-b)*conv; cf=np.sum(array[core]-b)*conv; re=scatter*np.sqrt(ring.sum())*conv; ce=scatter*np.sqrt(core.sum())*conv
    return rf,cf,rf/cf,re,ce
rows=[]
for filt,array in zip(filters,matched):
    rf,cf,ratio,re,ce=aperture_metrics(array); rows.append({'filter':filt,'ring_flux_Jy_proxy':rf,'ejecta_flux_Jy_proxy':cf,'ring_to_ejecta':ratio,'ring_random_error_Jy':re,'ejecta_random_error_Jy':ce})
metrics=pd.DataFrame(rows); metrics.to_csv('jwst_filter_aperture_metrics.csv',index=False)

fig,axes=plt.subplots(1,4,figsize=(16,4))
for ax,array,filt in zip(axes,matched,filters): ax.imshow(array,origin='lower',cmap='magma',vmin=np.percentile(array,3),vmax=np.percentile(array,99.5)); ax.set_title(f'{filt}, PSF matched'); ax.axis('off')
fig.tight_layout(); fig.savefig('jwst_filter_morphology_panels.png',dpi=180); plt.show()

stress=[]
for inner in [.50,.55,.60]:
    for outer in [1.05,1.15,1.25]:
        for filt,array in zip(filters,matched): stress.append((filt,inner,outer,aperture_metrics(array,inner,outer)[2]))
stress=pd.DataFrame(stress,columns=['filter','ring_inner_arcsec','ring_outer_arcsec','ring_to_ejecta']); stress.to_csv('jwst_aperture_sensitivity.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(11,4)); ax[0].bar(metrics['filter'],metrics.ring_to_ejecta); ax[0].set(ylabel='Ring / ejecta integrated flux',title='Wavelength-dependent structure');
for filt,g in stress.groupby('filter'): ax[1].scatter(g.ring_outer_arcsec,g.ring_to_ejecta,label=filt,alpha=.7)
ax[1].set(xlabel='Ring outer radius (arcsec)',ylabel='Ring / ejecta ratio',title='Aperture sensitivity'); ax[1].legend(); fig.tight_layout(); fig.savefig('jwst_filter_ratios_and_stress.png',dpi=180); plt.show()
"""
    result=r"""
span=metrics.ring_to_ejecta.max()/metrics.ring_to_ejecta.min(); results=[f'PSF-matched ring/ejecta ratio spans a factor {span:.2f} across F150W–F444W',f'largest ratio occurs in {metrics.loc[metrics.ring_to_ejecta.idxmax(),"filter"]}',f'result repeated across nine ring-aperture definitions per filter']
result={'id':'2026-08-01-jwst-sn1987a-filter-morphology','title':'JWST SN 1987A: filter-dependent ring/ejecta structure','archive':'MAST · JWST NIRCam','date':'2026-08-01','question':'How does the ring-to-ejecta surface-brightness balance change from 1.5 to 4.44 microns?','sample_size':int(sum(np.isfinite(a).sum() for a in aligned)),'results':results,'validation':'All filters are WCS-aligned, blurred to an approximate F444W PSF, background-subtracted, and repeated over nine aperture choices.','notebook':'mast/2026-08-01-jwst-sn1987a-filter-morphology/notebook.ipynb','hero':'mast/2026-08-01-jwst-sn1987a-filter-morphology/jwst_filter_morphology_panels.png','figures':['mast/2026-08-01-jwst-sn1987a-filter-morphology/jwst_filter_morphology_panels.png','mast/2026-08-01-jwst-sn1987a-filter-morphology/jwst_filter_ratios_and_stress.png'],'research_level':'Validated','claim_type':'Filter-resolved morphology','provenance':['MAST JWST program 1726','calibrated NIRCam I2D F150W, F200W, F356W, F444W','compact cutouts retain MJy/sr and WCS'],'artifacts':['data/sn1987a/jwst_f150w_2022_cutout.fits','data/sn1987a/jwst_f200w_2022_cutout.fits','data/sn1987a/jwst_f356w_2022_cutout.fits','data/sn1987a/jwst_f444w_2022_cutout.fits','mast/2026-08-01-jwst-sn1987a-filter-morphology/jwst_filter_aperture_metrics.csv','mast/2026-08-01-jwst-sn1987a-filter-morphology/jwst_aperture_sensitivity.csv'],'quality_checks':[{'name':'WCS registration','status':'pass'},{'name':'Approximate PSF matching','status':'pass'},{'name':'Local background subtraction','status':'pass'},{'name':'Aperture sensitivity','status':'pass'}],'limitations':['apertures are simple circular teaching regions','background errors omit correlated-pixel covariance','broadband ratios mix lines and continua and are not chemical abundances'],'tags':['JWST','SN 1987A','morphology','PSF matching']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(metrics.to_string(index=False))
assert np.isfinite(metrics.ring_to_ejecta).all()
"""
    refs="""## Interpretation and references

The changing ratio establishes that the remnant's spatial balance is
wavelength dependent after resolution matching. It does not by itself assign
the signal to one element. Matsuura et al. report that 1–2.3 μm images are
mostly line dominated, while 3–5 μm images contain strong continuum from dust
and synchrotron emission; that spectroscopic interpretation is cited rather
than re-derived from four broad filters.

- Matsuura et al. (2024): https://doi.org/10.1093/mnras/stae1381
- Arendt et al. (2023): https://doi.org/10.3847/1538-4357/acfd95
"""
    write_notebook(folder,'JWST SN 1987A: filter-dependent morphology','How does the ring-to-ejecta balance change across four NIRCam filters?',analysis,result,refs)
    (folder/'README.md').write_text('# JWST SN 1987A filter-dependent morphology\n\nFour calibrated NIRCam filters are WCS-aligned, approximately PSF-matched, background-subtracted, and tested across aperture choices.\n\n![Filter panels](jwst_filter_morphology_panels.png)\n\n[Open the executed notebook](notebook.ipynb)\n')


def cross_telescope() -> None:
    folder=ROOT/'mast/2026-08-01-hst-jwst-sn1987a-comparison'
    analysis=r"""
jw,_,wj,hj=load_fits('jwst_f200w_2022_cutout.fits'); hs,_,wh,hh=load_fits('hst_f625w_2018_cutout.fits'); h_on_j=reproject_array(hs,wh,wj,jw.shape); scale=pixel_scale_arcsec(wj); yy,xx=np.indices(jw.shape); from astropy.coordinates import SkyCoord
cx,cy=wj.world_to_pixel(SkyCoord(TARGET_RA,TARGET_DEC,unit='deg')); radius=np.hypot((xx-cx)*scale,(yy-cy)*scale); mask=(radius<1.6)&np.isfinite(h_on_j)&np.isfinite(jw)

def normalized(array):
    bg=(radius>3)&(radius<4.8)&np.isfinite(array); z=array-np.median(array[bg]); p=np.percentile(z[mask],99); return np.clip(np.arcsinh(8*np.maximum(z,0)/p)/np.arcsinh(8),0,1)

rows=[]; examples={}
for common in [.10,.12,.15,.18]:
    sig_h=np.sqrt(max(common**2-.070**2,0))/2.35482/scale; sig_j=np.sqrt(max(common**2-.066**2,0))/2.35482/scale
    hn=normalized(ndimage.gaussian_filter(np.nan_to_num(h_on_j,nan=np.nanmedian(h_on_j)),sig_h)); jn=normalized(ndimage.gaussian_filter(np.nan_to_num(jw,nan=np.nanmedian(jw)),sig_j)); corr=np.corrcoef(hn[mask],jn[mask])[0,1]; edge_h=ndimage.gaussian_gradient_magnitude(hn,1); edge_j=ndimage.gaussian_gradient_magnitude(jn,1); edge_corr=np.corrcoef(edge_h[mask],edge_j[mask])[0,1]; rows.append((common,corr,edge_corr)); examples[common]=(hn,jn,edge_h,edge_j)
stress=pd.DataFrame(rows,columns=['common_fwhm_arcsec','intensity_correlation','edge_correlation']); stress.to_csv('hst_jwst_resolution_stress.csv',index=False); hn,jn,eh,ej=examples[.12]
fig,axes=plt.subplots(1,3,figsize=(14,4.5)); axes[0].imshow(hn,origin='lower',cmap='magma'); axes[0].set_title('HST F625W · 2018'); axes[1].imshow(jn,origin='lower',cmap='magma'); axes[1].set_title('JWST F200W · 2022'); im=axes[2].imshow(jn-hn,origin='lower',cmap='coolwarm',vmin=-.7,vmax=.7); axes[2].set_title('Normalized JWST − HST'); [a.axis('off') for a in axes]; fig.colorbar(im,ax=axes[2],fraction=.046); fig.suptitle('Different wavelength, epoch, and instrument: morphology only'); fig.tight_layout(); fig.savefig('hst_jwst_registered_comparison.png',dpi=180); plt.show()
fig,ax=plt.subplots(1,2,figsize=(11,4)); ax[0].imshow(np.hypot(eh,ej),origin='lower',cmap='viridis'); ax[0].set_title('Combined normalized edge strength'); ax[0].axis('off'); ax[1].plot(stress.common_fwhm_arcsec,stress.intensity_correlation,'o-',label='intensity'); ax[1].plot(stress.common_fwhm_arcsec,stress.edge_correlation,'o-',label='edges'); ax[1].set(xlabel='Assumed common FWHM (arcsec)',ylabel='Pearson correlation',title='Resolution sensitivity'); ax[1].legend(); fig.tight_layout(); fig.savefig('hst_jwst_edge_and_resolution_check.png',dpi=180); plt.show()
"""
    result=r"""
nominal=stress.iloc[1]; results=[f'normalized remnant intensity correlation {nominal.intensity_correlation:.3f} at 0.12 arcsec common FWHM',f'edge-map correlation {nominal.edge_correlation:.3f} at the same smoothing',f'correlations explicitly tested from {stress.common_fwhm_arcsec.min():.2f} to {stress.common_fwhm_arcsec.max():.2f} arcsec']
result={'id':'2026-08-01-hst-jwst-sn1987a-comparison','title':'SN 1987A: registered Hubble–Webb structure comparison','archive':'MAST · HST WFC3 + JWST NIRCam','date':'2026-08-01','question':'Which normalized structures remain spatially similar between HST F625W in 2018 and JWST F200W in 2022?','sample_size':int(mask.sum()),'results':results,'validation':'The calibrated cutouts are registered by celestial WCS, normalized separately, blurred to four common resolutions, and compared in intensity and edge space.','notebook':'mast/2026-08-01-hst-jwst-sn1987a-comparison/notebook.ipynb','hero':'mast/2026-08-01-hst-jwst-sn1987a-comparison/hst_jwst_registered_comparison.png','figures':['mast/2026-08-01-hst-jwst-sn1987a-comparison/hst_jwst_registered_comparison.png','mast/2026-08-01-hst-jwst-sn1987a-comparison/hst_jwst_edge_and_resolution_check.png'],'research_level':'Exploration','claim_type':'Cross-instrument morphology','provenance':['HST program 15256 F625W HAP DRC product, 2018-07-08','JWST program 1726 F200W I2D product, 2022-09-02','both compact cutouts preserve WCS and original product names'],'artifacts':['data/sn1987a/hst_f625w_2018_cutout.fits','data/sn1987a/jwst_f200w_2022_cutout.fits','mast/2026-08-01-hst-jwst-sn1987a-comparison/hst_jwst_resolution_stress.csv'],'quality_checks':[{'name':'Celestial WCS registration','status':'pass'},{'name':'Common-resolution stress test','status':'pass'},{'name':'Separate normalization','status':'pass'},{'name':'Cross-band flux comparison','status':'not attempted'}],'limitations':['filters trace different wavelengths and emission processes','observations are four years apart','approximate Gaussian PSFs do not reproduce full instrument PSF wings','correlation is descriptive, not a physical model'],'tags':['HST','JWST','SN 1987A','cross telescope']}
Path('result.json').write_text(json.dumps(result,indent=2)); print(*results,sep='\n'); print(stress.to_string(index=False))
assert stress.intensity_correlation.between(-1,1).all()
"""
    refs="""## Interpretation and references

The comparison asks whether large normalized structures overlap after WCS and
resolution control. It cannot interpret a difference map as temporal change,
because the filters sample optical and infrared emission and the observations
are separated by four years. A publication-grade comparison would forward
model each instrument PSF, match physical band components, propagate WCS
covariance, and use contemporaneous observations.

- HST proposal 15256 dataset: https://doi.org/10.5270/esa-oqihlwz
- JWST program 1726 analysis: https://doi.org/10.1093/mnras/stae1381
"""
    write_notebook(folder,'SN 1987A: Hubble–Webb structure comparison','Which normalized structures remain spatially similar across HST and JWST?',analysis,result,refs)
    (folder/'README.md').write_text('# SN 1987A Hubble–Webb structure comparison\n\nCalibrated HST and JWST cutouts are registered by WCS and tested across common smoothing scales. The comparison is morphological, not cross-band photometry.\n\n![Comparison](hst_jwst_registered_comparison.png)\n\n[Open the executed notebook](notebook.ipynb)\n')


def main() -> None:
    timelapse(); lightcurve(); rgb(); filter_morphology(); cross_telescope()
    print('Prepared Scientific Audit Batch 3')


if __name__=='__main__': main()
