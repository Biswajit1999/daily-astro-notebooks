"""Read a *small real DR1-F pilot region* from public IRSA HATS files.
No simulation, imputation, synthetic-data fallback, or discovery claims.
The preregistered 1.25-deg full-field hypothesis remains untested here.
"""
import json
import traceback
from datetime import datetime,timezone
from pathlib import Path
import lsdb
from analyse_day01 import aggregate_halpha_fits

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

def actual_analysis(mer, spe, line):
    """Archive the line-selected sample before the separate MER morphology join."""
    line_names = line.spe_line_name.str.strip()
    report["pilot_line_label_counts"] = line_names.value_counts().head(30).to_dict()
    ha = aggregate_halpha_fits(line)
    primary = spe.loc[spe.spe_rank.eq(0), ["object_id", "spe_z", "spe_z_prob"]]
    joined = mer.merge(primary, on="object_id", validate="one_to_one").merge(
        ha, on="object_id", validate="one_to_one"
    )
    joined.to_csv(OUT / "joined_halpha_pilot.csv.gz", index=False, compression="gzip")
    selected = joined.loc[
        joined.spe_z.between(0.9, 1.5) & joined.spe_z_prob.ge(0.99)
        & joined.vis_det.eq(1) & joined.flux_vis_2fwhm_aper.gt(0)
    ]
    selected.to_csv(OUT / "selected_halpha_pilot.csv.gz", index=False, compression="gzip")
    report.update({
        "status": "LINE_SELECTION_COMPLETE; morphology join requires the original tile catalogue",
        "n_halpha_with_eligible_fit": len(ha),
        "n_joint_Halpha_pilot": len(joined),
        "n_line_selected_pilot": len(selected),
    })


def main():
 try:
  mer=load("mer_catalogue_deep_survey",CATALOGS["mer_catalogue_deep_survey"])
  spe=load("spectro_z_spe_galaxy_candidates_deep",CATALOGS["spectro_z_spe_galaxy_candidates_deep"])
  line=load("spectro_line_features_spe_line_features_deep",CATALOGS["spectro_line_features_spe_line_features_deep"])
  actual_analysis(mer,spe,line)
 except Exception as exc:
  report["status"]="FAILED";report["error"]=str(exc);report["traceback"]=traceback.format_exc()
  print("PILOT FAILED:",traceback.format_exc(),flush=True)
  raise
 finally:
  save()
  print("REPORT",json.dumps({k:v for k,v in report.items() if k!="catalogues"},default=str),flush=True)
if __name__=="__main__":main()
