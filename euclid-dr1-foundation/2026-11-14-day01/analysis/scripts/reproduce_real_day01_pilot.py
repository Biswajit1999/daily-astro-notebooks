"""Recompute Day 01 exploratory figures from public Euclid DR1-F HATS/FITS extracts.
Input folders are downloaded from the archival GitHub Actions runs.
There is NO confirmed full-field hypothesis test in this pilot.
"""
from pathlib import Path
import sys,json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
P=Path(sys.argv[1]);M=Path(sys.argv[2]);O=Path(sys.argv[3]);O.mkdir(parents=True,exist_ok=True)
figdir=O/"figures";figdir.mkdir(exist_ok=True)
rng=np.random.default_rng(20261114)
mer=pd.read_csv(P/"mer_catalogue_deep_survey.csv.gz")
spe=pd.read_csv(P/"spectro_z_spe_galaxy_candidates_deep.csv.gz")
line=pd.read_csv(P/"spectro_line_features_spe_line_features_deep.csv.gz")
spe=spe[spe.spe_rank==0]
ha=line[(line.spe_rank==0)&(line.spe_line_name=="Halpha")]
valid=(ha.spe_line_flux_gf>0)&(ha.spe_line_flux_err_gf>0)&(ha.spe_line_snr_gf>=5)
ha=ha[valid].groupby("object_id",as_index=False).agg(
 ha_flux=("spe_line_flux_gf","median"),ha_snr=("spe_line_snr_gf","median"),
 ha_wl=("spe_line_central_wl_gf","median"),n_line_entries=("spe_line_flux_gf","size"))
d=mer.merge(spe[["object_id","spe_z","spe_z_prob"]],on="object_id",validate="one_to_one").merge(ha,on="object_id",validate="one_to_one")
d=d[d.spe_z.between(.9,1.5)&(d.spe_z_prob>=.99)&(d.vis_det==1)&(d.flux_vis_2fwhm_aper>0)].copy()
assert len(d)==426 and d.object_id.is_unique
d.to_csv(O/"selected_426.csv",index=False)
full=pd.read_csv(M/"mer_final_size_fields.csv.gz",usecols=["object_id","kron_radius","flag_vis","det_quality_flag","spurious_prob"])
s=d.merge(full,on="object_id",validate="one_to_one")
s=s[(s.kron_radius>0)&np.isfinite(s.kron_radius)].copy()
assert len(s)==327
quality=s[(s.flag_vis==0)&(s.det_quality_flag==0)&(s.spurious_prob<.5)].copy()
assert len(quality)==150
s.to_csv(O/"size_matched_327.csv",index=False)
quality.to_csv(O/"strict_quality_150.csv",index=False)
bins=pd.cut(s.spe_z,[.9,1.1,1.3,1.5],right=False,include_lowest=True)
cells=[]
for b in bins.cat.categories:
 t=s[bins==b]
 group=pd.qcut(t.flux_vis_2fwhm_aper,3,duplicates="drop")
 for c in group.cat.categories:
  cell=t[group==c].copy()
  cell["grp"]=(cell.ha_flux>cell.ha_flux.median()).astype(int)
  if len(cell)>=20 and min((cell.grp==0).sum(),(cell.grp==1).sum())>=10:
   cells.append(cell)
def effect(items):
 vals=[np.log10(c.loc[c.grp==1,"kron_radius"]).median()-np.log10(c.loc[c.grp==0,"kron_radius"]).median() for c in items]
 return float(np.average(vals,weights=[len(c) for c in items]))
e=effect(cells)
pr=np.empty(2000)
for i in range(2000):
 t=[]
 for c in cells:
  x=c.copy();x["grp"]=rng.permutation(c.grp.to_numpy());t.append(x)
 pr[i]=effect(t)
p=(1+(np.abs(pr)>=abs(e)).sum())/2001
rho=float(spearmanr(d.ha_flux,d.flux_vis_2fwhm_aper).statistic)
metrics={"real_data":True,"field":"EDFN 0.15 deg cone","release":"Euclid DR1-Foundation",
 "n_mer":len(mer),"n_spe_rank0":len(spe),"n_line_rows":len(line),
 "n_ha_selected":len(d),"n_size_matched":len(s),"n_strict_quality":len(quality),
 "spearman_Halpha_VIS":rho,"pilot_unflagged_size_effect_dex":e,"pilot_unflagged_permutation_p":p,
 "gate":"NO-GO: only 150 strictly clean matched galaxies; preregistration requires >=200",
 "note":"Exploratory single-tile analysis; no completeness model; this is not the complete 1.25-degree test"}
(O/"analysis_metrics.json").write_text(json.dumps(metrics,indent=2))
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
def save(fig,name):
 fig.tight_layout();fig.savefig(figdir/name,dpi=200);plt.close(fig)
f,a=plt.subplots(figsize=(7,5));im=a.scatter(d.ra,d.dec,c=d.spe_z,s=12,alpha=.8,cmap="viridis");a.invert_xaxis()
a.set(xlabel="RA (deg, ICRS)",ylabel="Dec (deg, ICRS)",title="Euclid DR1-F Halpha sample (426 unique objects)")
f.colorbar(im,ax=a,label="Redshift");save(f,"01_actual_sky_map.png")
f,a=plt.subplots(figsize=(7,5));im=a.scatter(d.spe_z,d.ha_flux,c=d.flux_vis_2fwhm_aper,s=14,cmap="plasma",norm=matplotlib.colors.LogNorm())
a.set(yscale="log",xlabel="SPE rank-0 redshift",ylabel="Halpha Gaussian-fit flux (erg/s/cm2)",title="Halpha line flux versus redshift (selected detections)")
f.colorbar(im,ax=a,label="VIS aperture flux (microJy)");save(f,"02_actual_line_flux_redshift.png")
f,a=plt.subplots(figsize=(7,5));im=a.scatter(d.flux_vis_2fwhm_aper,d.ha_flux,c=d.spe_z,s=15,alpha=.7)
a.set(xscale="log",yscale="log",xlabel="VIS 2-FWHM flux (microJy)",ylabel="Halpha Gaussian-fit flux (erg/s/cm2)",title=f"Observed, selection-dependent trend: rho={rho:.3f}")
f.colorbar(im,ax=a,label="Redshift");save(f,"03_actual_line_VIS_association.png")
f,a=plt.subplots(figsize=(7,5));im=a.scatter(s.ha_flux,s.kron_radius,c=s.flux_vis_2fwhm_aper,s=16,alpha=.7,norm=matplotlib.colors.LogNorm())
a.set(xscale="log",yscale="log",xlabel="Halpha line flux (erg/s/cm2)",ylabel="MER Kron radius (pixels)",title="Pilot size/line relation (327 records, not quality-gated)")
f.colorbar(im,ax=a,label="VIS flux (microJy)");save(f,"04_actual_size_relation_pilot.png")
f,a=plt.subplots(figsize=(7,4));a.hist(pr,bins=45,color="steelblue",alpha=.8);a.axvline(e,color="darkred",ls="--",lw=2)
a.set(xlabel="High minus low Halpha log(Kron) contrast (dex)",ylabel="Permutations",title=f"Provisional (not quality-gated) shuffle test; p={p:.3f}")
save(f,"05_provisional_size_permutation.png")
f,a=plt.subplots(figsize=(7,5));a.scatter(s.ha_flux,s.kron_radius,s=16,color="tab:orange",alpha=.4,label=f"All matched (n={len(s)})")
a.scatter(quality.ha_flux,quality.kron_radius,s=19,color="tab:blue",alpha=.75,label=f"Strict clean (n={len(quality)})")
a.set(xscale="log",yscale="log",xlabel="Halpha line flux (erg/s/cm2)",ylabel="Kron radius (pixels)",title="Photometric quality-flag gate reduces sample")
a.legend();save(f,"06_strict_flag_quality_gate.png")
f,a=plt.subplots(figsize=(7,4));delta=d.ha_wl/(1+d.spe_z)-6564.61;a.hist(delta,bins=42,color="steelblue")
a.axvline(0,ls="--",color="black");a.set(xlabel="Rest-frame line-centre residual (Angstrom)",ylabel="Distinct catalogue objects",title="Pipeline Halpha identification consistency check")
save(f,"07_Halpha_restframe_linecentre.png")
print(json.dumps(metrics,indent=2))
