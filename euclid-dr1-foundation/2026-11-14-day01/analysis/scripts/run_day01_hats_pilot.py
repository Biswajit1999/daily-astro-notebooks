"""Read a *small real DR1-F pilot region* from public IRSA HATS files.
No simulation, imputation, synthetic-data fallback, or discovery claims.
The preregistered 1.25-deg full-field hypothesis remains untested here.
"""
import json
import traceback
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lsdb

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"pilot_real"
OUT.mkdir(parents=True,exist_ok=True)
BASE="s3://nasa-irsa-euclid-dr1/contributed/dr1/hats/reformatted_catalogs/"
CENTER_RA=269.733
CENTER_DEC=66.018
RADIUS_DEG=0.15
CATALOGS={
 "mer_catalogue_deep_survey": ["object_id","ra","dec","right_ascension","declination","tileid","tile_index","kron_radius","vis_det","flag_vis","det_quality_flag","spurious_prob","flux_vis_2fwhm_aper"],
 "spectro_z_spe_galaxy_candidates_deep":["object_id","spe_rank","spe_z","spe_z_prob","spe_z_rel"],
 "spectro_line_features_spe_line_features_deep":["object_id","spe_rank","spe_line_name","spe_line_flag","spe_line_flux_gf","spe_line_flux_err_gf","spe_line_snr_gf","spe_line_qual_gf","spe_line_central_wl_gf"]
}
report={"release":"Euclid DR1-Foundation","date_utc":datetime.now(timezone.utc).isoformat(),"mode":"pilot, not preregistered confirmatory test","field_center_deg":[CENTER_RA,CENTER_DEC],"pilot_radius_deg":RADIUS_DEG,"catalogues":{},"status":"STARTED"}
def save():
 (OUT/"pilot_summary.json").write_text(json.dumps(report,indent=2,default=str))
def load(name, desired):
 path=BASE+name+"/"
 print("OPEN",path,flush=True)
 options={"anon":True}
 source=lsdb.open_catalog(path,storage_options=options,search_filter=lsdb.ConeSearch(CENTER_RA,CENTER_DEC,RADIUS_DEG*3600))
 available=list(source.dtypes.index)
 selected=[x for x in desired if x in available]
 report["catalogues"][name]={"path":path,"available_columns":available,"selected_columns":selected}
 if "object_id" not in selected:
  raise RuntimeError(f"object_id not present in {name}; available: {available[:60]}")
 # Reload with selected fields to take advantage of Parquet column pruning.
 selected_cat=lsdb.open_catalog(path,storage_options=options,search_filter=lsdb.ConeSearch(CENTER_RA,CENTER_DEC,RADIUS_DEG*3600),columns=selected)
 tab=selected_cat.compute().reset_index(drop=True)
 tab.columns=[str(x).lower() for x in tab.columns]
 report["catalogues"][name]["n_rows"]=int(len(tab))
 report["catalogues"][name]["dtypes"]={x:str(v) for x,v in tab.dtypes.items()}
 tab.to_csv(OUT/(name+".csv.gz"),index=False,compression="gzip")
 print("LOADED",name,len(tab),"columns:",list(tab.columns),flush=True)
 return tab

def actual_analysis(mer,spe,line):
 for f in ["ra","dec"]:
  if f not in mer and {"right_ascension","declination"}.issubset(mer):
   mer=mer.rename(columns={"right_ascension":"ra","declination":"dec"})
 if "spe_line_name" not in line: raise RuntimeError("SPE line-name column missing")
 line["spe_line_name"]=line.spe_line_name.astype(str).str.strip()
 counts=line.spe_line_name.value_counts().head(30)
 report["pilot_line_label_counts"]=counts.to_dict()
 print("LINE LABEL COUNTS",counts.to_dict(),flush=True)
 ha_names=[x for x in counts.index if x.lower().replace("_","").replace(" ","").replace("-","") in ["halpha","ha","hα","h1alpha"]]
 if not ha_names:
  report["status"]="NO_HALPHA_LABEL_IN_PILOT; do not invent labels"
  return
 main=line[line.spe_line_name.isin(ha_names) & (line.spe_rank==0)].copy()
 spe=spe[spe.spe_rank==0].copy()
 # Avoid many-to-many multiplication across repeated object records.
 for name,data in [("mer",mer),("spe",spe),("line",main)]:
  ndup=int(data.object_id.duplicated(keep=False).sum())
  report["duplicate_rows_"+name]=ndup
  data.drop(data.index[data.object_id.duplicated(keep=False)],inplace=True)
 combined=mer.merge(spe,on="object_id",how="inner",validate="one_to_one").merge(main,on=["object_id","spe_rank"],how="inner",validate="one_to_one")
 report["n_joint_Halpha_pilot"]=int(len(combined))
 combined.to_csv(OUT/"joined_halpha_pilot.csv.gz",index=False,compression="gzip")
 if len(combined)==0:
  report["status"]="NO_JOINT_HA_OBJECTS_IN_PILOT"
  return
 cuts=np.ones(len(combined),dtype=bool)
 for key,lim in [("spe_z",(0.9,1.5)),("spe_line_snr_gf",(5,np.inf)),("spe_z_prob",(0.99,np.inf))]:
  if key in combined:
   vals=pd.to_numeric(combined[key],errors="coerce")
   cuts &= vals.between(lim[0],lim[1],inclusive="both").to_numpy()
 for key in ["kron_radius","spe_line_flux_gf","spe_line_flux_err_gf","flux_vis_2fwhm_aper"]:
  if key in combined: cuts &= (pd.to_numeric(combined[key],errors="coerce")>0).to_numpy()
 for key,value in [("vis_det",1),("flag_vis",0),("det_quality_flag",0)]:
  if key in combined: cuts &= (pd.to_numeric(combined[key],errors="coerce")==value).to_numpy()
 clean=combined[cuts].copy()
 report["n_quality_cut_pilot"]=len(clean)
 clean.to_csv(OUT/"selected_halpha_pilot.csv",index=False)
 if len(clean)==0:
  report["status"]="ZERO_AFTER_QA_CUTS; investigate before changing cuts"
  return
 report["descriptive_pilot"]={"n":len(clean),"median_z":float(clean.spe_z.median()),"median_kron_radius_pix":float(clean.kron_radius.median()),"median_line_flux":float(clean.spe_line_flux_gf.median())}
 if {"ra","dec"}.issubset(clean.columns):
  f,ax=plt.subplots(figsize=(6,4.5))
  ax.scatter(clean.ra,clean.dec,s=12,alpha=.6)
  ax.invert_xaxis()
  ax.set(xlabel="RA (deg)",ylabel="Dec (deg)",title=f"Euclid DR1-F pilot Hα sample; n={len(clean)}")
  f.tight_layout()
  f.savefig(OUT/"pilot_sky_map.png",dpi=180);plt.close(f)
 if len(clean)>2:
  f,ax=plt.subplots(figsize=(6,4.5))
  ax.scatter(clean.spe_z,np.log10(clean.spe_line_flux_gf),s=12,alpha=.65)
  ax.set(xlabel="SPE z",ylabel="log10 Hα Gaussian-fit flux (erg/s/cm²)",title="Detected-line sample; not completeness-corrected")
  f.tight_layout();f.savefig(OUT/"pilot_line_flux_redshift.png",dpi=180);plt.close(f)
  f,ax=plt.subplots(figsize=(6,4.5))
  ax.scatter(np.log10(clean.spe_line_flux_gf),np.log10(clean.kron_radius),s=12,alpha=.65)
  ax.set(xlabel="log10 Hα line flux (erg/s/cm²)",ylabel="log10 Kron aperture radius (pixels)",title="Pilot unadjusted diagnostic; not a size–SFR result")
  f.tight_layout();f.savefig(OUT/"pilot_lineflux_aperture.png",dpi=180);plt.close(f)
 report["status"]="PILOT_DESCRIPTIVES_ONLY; primary 1.25-degree preregistered test not run"
def main():
 try:
  mer=load("mer_catalogue_deep_survey",CATALOGS["mer_catalogue_deep_survey"])
  spe=load("spectro_z_spe_galaxy_candidates_deep",CATALOGS["spectro_z_spe_galaxy_candidates_deep"])
  line=load("spectro_line_features_spe_line_features_deep",CATALOGS["spectro_line_features_spe_line_features_deep"])
  actual_analysis(mer,spe,line)
 except Exception as exc:
  report["status"]="FAILED";report["error"]=str(exc);report["traceback"]=traceback.format_exc()
  print("PILOT FAILED:",traceback.format_exc(),flush=True)
 finally:
  save()
  print("REPORT",json.dumps({k:v for k,v in report.items() if k!="catalogues"},default=str),flush=True)
if __name__=="__main__":main()
