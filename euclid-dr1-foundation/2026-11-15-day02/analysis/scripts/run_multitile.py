"""Euclid DR1-Foundation Day 2: bounded multi-tile real-data follow-up.
No ML, no synthetic observations, no discovery claims.
Run on an environment with public IRSA S3 access.
"""
from pathlib import Path
from datetime import datetime, timezone
import os, json, hashlib, tempfile, traceback, warnings
import numpy as np
import pandas as pd
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from astropy.io import fits
import lsdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"observed_results"
FIG=OUT/"figures"
FIG.mkdir(parents=True,exist_ok=True)
BASE="s3://nasa-irsa-euclid-dr1/contributed/dr1/hats/reformatted_catalogs/"
RA,DEC,RADIUS=269.733,66.018,0.28
SEED=20261115
RNG=np.random.default_rng(SEED)
BUCKET="nasa-irsa-euclid-dr1"
CLIENT=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,read_timeout=90,retries={"max_attempts":3}))
manifest={"date_utc":datetime.now(timezone.utc).isoformat(),"data_release":"Euclid DR1-Foundation",
          "centre_icrs":[RA,DEC],"radius_deg":RADIUS,"mode":"exploratory extension, not Day01 preregistered full-field confirmation",
          "git_sha":os.environ.get("GITHUB_SHA"),"inputs":[],"steps":[]}
results={"status":"STARTED","gate":"NO-GO pending quality and novelty checks","selection":{},"robustness":{}}
def save():
 (OUT/"provenance.json").write_text(json.dumps(manifest,indent=2,default=str))
 (OUT/"metrics.json").write_text(json.dumps(results,indent=2,default=str))
def log(name,**kwargs):
 manifest["steps"].append({"step":name,**kwargs})
 print(name,kwargs,flush=True)
 save()
def get_cat(name,fields,condition=None):
 path=BASE+name+"/"
 src=lsdb.open_catalog(path,storage_options={"anon":True},search_filter=lsdb.ConeSearch(RA,DEC,RADIUS*3600),columns=fields)
 if condition:
  try:
   src=src.query(condition)
   print("PUSHDOWN",name,condition,flush=True)
  except Exception as ex:
   log("query_filter_not_supported",catalogue=name,error=str(ex))
 d=src.compute().reset_index(drop=True)
 d.columns=[str(x).lower() for x in d.columns]
 manifest["inputs"].append({"kind":"HATS","path":path,"fields":fields,"rows":len(d),"predicate":condition})
 log("loaded",catalogue=name,n=len(d))
 return d

def source_sample():
 m=get_cat("mer_catalogue_deep_survey",["object_id","ra","dec","tileid","vis_det","flux_vis_2fwhm_aper"])
 s=get_cat("spectro_z_spe_galaxy_candidates_deep",["object_id","spe_rank","spe_z","spe_z_prob"],"spe_rank == 0")
 l=get_cat("spectro_line_features_spe_line_features_deep",["object_id","spe_rank","spe_line_name","spe_line_flux_gf","spe_line_flux_err_gf","spe_line_snr_gf","spe_line_central_wl_gf"],"spe_rank == 0 and spe_line_name == 'Halpha'")
 s=s[s.spe_rank==0].copy()
 l=l[(l.spe_rank==0)&(l.spe_line_name.astype(str)=="Halpha")].copy()
 results["selection"].update({"mer_cone_rows":len(m),"spe_cone_rows":len(s),"halpha_rows_prevalid":len(l)})
 for name,df in [("MER HATS",m),("SPE rank0",s)]:
  if df.object_id.duplicated().any():
   raise ValueError(name+" duplicate object IDs; abort ambiguous join")
 valid=np.isfinite(pd.to_numeric(l.spe_line_flux_gf,errors="coerce")) & (l.spe_line_flux_gf>0)&(l.spe_line_flux_err_gf>0)&(l.spe_line_snr_gf>=5)
 l=l.loc[valid].copy()
 log("line_valid",rows=len(l),unique_objects=int(l.object_id.nunique()))
 a=l.groupby("object_id",as_index=False).agg(
  ha_flux=("spe_line_flux_gf","median"),ha_snr=("spe_line_snr_gf","median"),
  ha_err=("spe_line_flux_err_gf","median"),ha_wl=("spe_line_central_wl_gf","median"),
  n_valid_line_entries=("spe_line_flux_gf","size"),
  ha_flux_min=("spe_line_flux_gf","min"),ha_flux_max=("spe_line_flux_gf","max"))
 a["flux_range_over_median"]=(a.ha_flux_max-a.ha_flux_min)/a.ha_flux
 results["selection"]["multiple_valid_line_fits"]=int((a.n_valid_line_entries>1).sum())
 results["selection"]["multifit_spread_gt_20pct"]=int((a.flux_range_over_median>0.2).sum())
 d=m.merge(s[["object_id","spe_z","spe_z_prob"]],on="object_id",validate="one_to_one").merge(a,on="object_id",validate="one_to_one")
 results["selection"]["all_joined"]=len(d)
 d=d[(d.spe_z>=.9)&(d.spe_z<1.5)&(d.spe_z_prob>=.99)&(d.vis_det==1)&(d.flux_vis_2fwhm_aper>0)].copy()
 assert d.object_id.is_unique
 results["selection"]["spectral_and_vis"]=len(d)
 log("spectral_selection",objects=len(d),tiles=d.tileid.value_counts().sort_index().to_dict())
 d.to_csv(OUT/"selected_spe_mer.csv.gz",index=False,compression="gzip")
 return d

def fetch_morphology(early):
 tile_counts=early.tileid.value_counts().sort_index()
 tiles=[int(x) for x in tile_counts.index]
 if len(tiles)>25: raise RuntimeError(f"More than 25 tiles ({len(tiles)}); choose a smaller spatial region before extending.")
 rows=[]
 missed=[]
 all_ids=set(early.object_id.astype("int64").tolist())
 for tid in tiles:
  prefix=f"dr1/catalogs/MER_FINAL_CATALOG/{tid}/"
  listing=CLIENT.list_objects_v2(Bucket=BUCKET,Prefix=prefix,MaxKeys=150)
  options=[x for x in listing.get("Contents",[]) if "FINAL-CAT_" in x["Key"] and x["Key"].endswith(".fits") and "FINAL-MORPH" not in x["Key"]]
  if len(options)!=1:
   missed.append({"tile":tid,"count":len(options)})
   log("tile_ambiguous",tile=tid,count=len(options))
   continue
  item=options[0]
  f=tempfile.NamedTemporaryFile(delete=False,suffix=".fits")
  f.close()
  try:
   CLIENT.download_file(BUCKET,item["Key"],f.name)
   digest=hashlib.sha256()
   with open(f.name,"rb") as h:
    for chunk in iter(lambda:h.read(1024*1024),b""): digest.update(chunk)
   with fits.open(f.name,memmap=True) as hdus:
    table=next(h.data for h in hdus if hasattr(h,"columns") and "OBJECT_ID" in h.columns.names)
    ids=np.asarray(table["OBJECT_ID"],dtype="int64")
    matching_ids=np.array(list(all_ids.intersection(set(ids.tolist()))),dtype="int64")
    idx=np.isin(ids,matching_ids)
    picked=pd.DataFrame({
      "object_id":ids[idx],
      "kron_radius":np.asarray(table["KRON_RADIUS"][idx],dtype="float64"),
      "flag_vis":np.asarray(table["FLAG_VIS"][idx],dtype="float64"),
      "det_quality_flag":np.asarray(table["DET_QUALITY_FLAG"][idx],dtype="float64"),
      "spurious_prob":np.asarray(table["SPURIOUS_PROB"][idx],dtype="float64"),
      "mer_fits_tile":tid
    })
   picked.to_csv(OUT/f"mer_tile_{tid}_matched.csv",index=False)
   rows.append(picked)
   manifest["inputs"].append({"kind":"MER_FINAL-CAT FITS","tile":tid,"s3_key":item["Key"],"bytes":item["Size"],"sha256":digest.hexdigest(),"matched_rows":len(picked)})
   log("tile_complete",tile=tid,n_catalogue_matches=len(picked))
  finally:
   os.unlink(f.name)
 results["selection"]["missing_tile_catalogue"]=missed
 if missed: raise RuntimeError("Some tile FITS unavailable/ambiguous; result is incomplete, cannot infer")
 allm=pd.concat(rows,ignore_index=True)
 if allm.object_id.duplicated().any():
  # Never silently choose one duplicated morphology row.
  dup_ids=set(allm.loc[allm.object_id.duplicated(keep=False),"object_id"])
  results["selection"]["ambiguous_mer_object_ids"]=len(dup_ids)
  allm=allm[~allm.object_id.isin(dup_ids)]
 return allm

def cut_quality(d):
 quality=(d.kron_radius>0)&np.isfinite(d.kron_radius)&(d.flag_vis==0)&(d.det_quality_flag==0)&(d.spurious_prob>=0)&(d.spurious_prob<.5)
 clean=d.loc[quality].copy()
 d["clean"]=quality
 log("morphology_and_quality",matched=len(d),clean=len(clean),rejected=len(d)-len(clean))
 results["selection"].update({"morphology_matched":len(d),"clean_quality":len(clean),
 "tile_counts_pre":{str(k):int(v) for k,v in d.groupby("tileid").size().items()},
 "tile_counts_clean":{str(k):int(v) for k,v in clean.groupby("tileid").size().items()},
 "flag_vis_counts":{str(k):int(v) for k,v in d.flag_vis.value_counts(dropna=False).items()},
 "det_quality_counts":{str(k):int(v) for k,v in d.det_quality_flag.value_counts(dropna=False).items()}})
 d.to_csv(OUT/"all_morphology_matched.csv.gz",index=False,compression="gzip")
 clean.to_csv(OUT/"strict_clean.csv",index=False)
 return d,clean

def prepare_cells(frame):
 d=frame[(frame.kron_radius>0)&(frame.ha_flux>0)&(frame.flux_vis_2fwhm_aper>0)].copy()
 if len(d)<200: return [],"n below 200"
 d["z_bin"]=pd.cut(d.spe_z,[.9,1.1,1.3,1.5],right=False)
 cells=[]
 for z,zdf in d.groupby("z_bin",observed=True):
  if len(zdf)<60: continue
  zdf=zdf.copy()
  try: zdf["vis_bin"]=pd.qcut(zdf.flux_vis_2fwhm_aper,3,labels=False,duplicates="drop")
  except ValueError: continue
  for vb,group in zdf.groupby("vis_bin"):
   g=group.copy()
   mid=g.ha_flux.median()
   g["high_ha"]=(g.ha_flux>mid).astype("int8")
   if len(g)>=20 and min((g.high_ha==0).sum(),(g.high_ha==1).sum())>=10:
    cells.append(g)
 if len(cells)<4: return cells,"fewer than 4 cells"
 return cells,None

def statistic(cells):
 a=[];weights=[]
 for c in cells:
  hi=np.log10(c.loc[c.high_ha==1,"kron_radius"].to_numpy(dtype=float))
  lo=np.log10(c.loc[c.high_ha==0,"kron_radius"].to_numpy(dtype=float))
  a.append(float(np.median(hi)-np.median(lo)));weights.append(len(c))
 return float(np.average(a,weights=weights))

def infer(frame,seed,full=True):
 cells,error=prepare_cells(frame)
 output={"n_input":len(frame),"n_cells":len(cells),"n_in_cells":int(sum(len(c) for c in cells)),
         "cell_counts":[int(len(c)) for c in cells], "status":"INCONCLUSIVE" if error else "EXPLORATORY_ESTIMATE"}
 if error: output["reason"]=error;return output
 output["effect_dex"]=statistic(cells)
 output["size_ratio_proxy"]=float(10**output["effect_dex"])
 if not full: return output
 rg=np.random.default_rng(seed)
 perm=np.empty(2000)
 bootstrap=np.empty(2000)
 # Fixed memberships under the null. Distinct group-preserving bootstrap.
 inputs=[]
 for c in cells:
  x=np.log10(c.kron_radius.to_numpy(dtype=float))
  y=c.high_ha.to_numpy(dtype=int)
  inputs.append((x,y,len(c)))
 for it in range(2000):
  vals=[];boots=[];weights=[]
  for x,y,n in inputs:
   shuffle=rg.permutation(y)
   vals.append(np.median(x[shuffle==1])-np.median(x[shuffle==0]))
   high=x[y==1];low=x[y==0]
   boots.append(np.median(rg.choice(high,len(high),replace=True))-np.median(rg.choice(low,len(low),replace=True)))
   weights.append(n)
  perm[it]=np.average(vals,weights=weights)
  bootstrap[it]=np.average(boots,weights=weights)
 output.update({"permutation_two_sided_p":float((1+np.count_nonzero(abs(perm)>=abs(output["effect_dex"])))/(len(perm)+1)),
                "bootstrap_ci95_dex":[float(x) for x in np.quantile(bootstrap,[.025,.975])],
                "permutations":2000,"bootstrap_resamples":2000,"seed":seed})
 np.savez_compressed(OUT/"resampling_distributions.npz",permutation=perm,bootstrap=bootstrap)
 return output

def figures(d,c):
 plt.rcParams.update({"axes.spines.right":False,"axes.spines.top":False,"font.size":10})
 f,ax=plt.subplots(figsize=(7,5))
 for lab,keep,color in [("Strict clean",d.clean,"tab:blue"),("Flagged / excluded",~d.clean,"tab:orange")]:
  subset=d[keep];ax.scatter(subset.ra,subset.dec,s=6,alpha=.52,label=f"{lab} (n={len(subset)})",color=color)
 ax.set(xlabel="ICRS right ascension (deg)",ylabel="ICRS declination (deg)",title="Euclid DR1-F multi-tile pilot; individual released sources")
 ax.invert_xaxis();ax.legend();f.tight_layout();f.savefig(FIG/"01_sky_map_quality.png",dpi=175);plt.close(f)
 f,ax=plt.subplots(figsize=(7,5))
 ax.scatter(d.loc[~d.clean,"ha_flux"],d.loc[~d.clean,"kron_radius"],s=9,alpha=.18,label="Flagged",color="tab:orange")
 ax.scatter(c.ha_flux,c.kron_radius,s=12,alpha=.5,label="Strict clean",color="tab:blue")
 ax.set(xscale="log",yscale="log",xlabel="Pipeline Halpha line flux (erg s^-1 cm^-2)",ylabel="Pipeline MER Kron aperture semi-major axis (pixels)",
        title="Quality-sensitive size–line-flux diagnostic (not intrinsic galaxy sizes)")
 ax.legend();f.tight_layout();f.savefig(FIG/"02_size_lineflux_by_quality.png",dpi=175);plt.close(f)
 f,ax=plt.subplots(figsize=(7,4))
 a=d.groupby(["tileid","clean"]).size().unstack(fill_value=0)
 a.rename(columns={False:"Excluded",True:"Strict clean"}).plot(kind="bar",ax=ax,color=["tab:orange","tab:blue"])
 ax.set(xlabel="Euclid MER tile ID",ylabel="Number of matched sources",title="Selection losses vary across tiles")
 ax.tick_params(axis="x",rotation=30)
 f.tight_layout();f.savefig(FIG/"03_tile_quality_attrition.png",dpi=175);plt.close(f)
 if (OUT/"resampling_distributions.npz").exists():
  arr=np.load(OUT/"resampling_distributions.npz")["permutation"]
  f,ax=plt.subplots(figsize=(7,4));ax.hist(arr,bins=45,color="0.55")
  if "effect_dex" in results["primary"]: ax.axvline(results["primary"]["effect_dex"],color="tab:red",ls="--")
  ax.set(xlabel="Permuted high–low Halpha log10(Kron) contrast (dex)",ylabel="Count",
         title="Exploratory within-cell permutation distribution")
  f.tight_layout();f.savefig(FIG/"04_exploratory_permutation.png",dpi=175);plt.close(f)

try:
 s=source_sample()
 m=fetch_morphology(s)
 d=s.merge(m,on="object_id",validate="one_to_one")
 allm,clean=cut_quality(d)
 results["selection"]["selected_without_morphology"]=len(s)-len(d)
 results["primary"]=infer(clean,SEED)
 for label,subset in [
   ("line_snr_ge_10",clean[clean.ha_snr>=10]),
   ("redshift_prob_ge_0_999",clean[clean.spe_z_prob>=.999]),
   ("redshift_0_95_to_1_45",clean[clean.spe_z.between(.95,1.45,inclusive="both")]),
 ]:
  results["robustness"][label]=infer(subset,SEED+17,full=False)
 results["robustness"]["leave_one_tile_out"]={}
 for tile in sorted(clean.tileid.unique()):
  results["robustness"]["leave_one_tile_out"][str(int(tile))]=infer(clean[clean.tileid!=tile],SEED+int(tile)%100,full=False)
 figures(allm,clean)
 if results["primary"]["status"]!="EXPLORATORY_ESTIMATE":
  results["status"]="INCONCLUSIVE_SAMPLE_GATE"
 else:
  results["status"]="EXPLORATORY_MULTI_TILE_ESTIMATE"
 # A nominal p-value does not override the incomplete preregistered field, selection function or audit.
 results["gate"]="NO-GO: incomplete 1.25-degree original field, selection function and novelty audit"
except Exception as exc:
 results["status"]="FAILED";results["error"]=str(exc);results["traceback"]=traceback.format_exc()
 print("ERROR",traceback.format_exc(),flush=True)
finally:
 save()
 print("DONE",json.dumps({k:v for k,v in results.items() if k!="robustness"},default=str),flush=True)
