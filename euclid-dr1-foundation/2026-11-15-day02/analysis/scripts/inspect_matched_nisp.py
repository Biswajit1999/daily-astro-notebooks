"""Check object-specific real Euclid DR1-F SIR combined spectra for Day 02 emitters.
Catalogued Halpha is a pipeline claim; direct 1D inspection is only a consistency check.
No machine learning, synthetic data, or invented line detection.
"""
from pathlib import Path
from datetime import datetime, timezone
import tempfile, os, json, traceback, re
import numpy as np
import pandas as pd
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from astropy.io import fits
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"observed_results"/"matched_spectra"
OUT.mkdir(parents=True,exist_ok=True)
CLEAN=pd.read_csv(ROOT/"observed_results"/"strict_clean.csv")
BUCKET="nasa-irsa-euclid-dr1"
S3=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,read_timeout=70,retries={"max_attempts":3}))
LINE_A=6564.61
REPORT={"created_utc":datetime.now(timezone.utc).isoformat(),"release":"Euclid DR1-Foundation",
        "purpose":"direct identification of released 1D SIR spectra corresponding to quality-gated Halpha objects",
        "examined_tiles":[],"candidates_found":0,"plotted":0,"plots":[],"errors":[],"warning":"Do not claim flux-calibrated spectroscopic validation without checking the product units, extraction geometry and line contamination."}
def save():
 (OUT/"matched_spectrum_audit.json").write_text(json.dumps(REPORT,indent=2,default=str))
def inspect(tile):
 prefix=f"dr1/SIR_COMBINED_SPECTRA/{tile}/"
 o=S3.list_objects_v2(Bucket=BUCKET,Prefix=prefix,MaxKeys=100)
 files=[v for v in o.get("Contents",[]) if "W-COMBSPEC" in v["Key"] and v["Key"].endswith(".fits")]
 info={"tile":tile,"file_count":len(files),"matches":[]}
 REPORT["examined_tiles"].append(info)
 if not files:return
 valid=CLEAN[CLEAN.tileid==int(tile)].set_index("object_id",drop=False)
 for obj in files[:2]:
  local=tempfile.NamedTemporaryFile(delete=False,suffix=".fits")
  local.close()
  try:
   print("DOWNLOAD",obj["Key"],obj["Size"],flush=True)
   S3.download_file(BUCKET,obj["Key"],local.name)
   with fits.open(local.name,memmap=True,lazy_load_hdus=True) as hdus:
    hdunames={h.name.upper():i for i,h in enumerate(hdus)}
    report_meta=0
    for i,h in enumerate(hdus):
     if not h.name.upper().endswith("_META"):continue
     report_meta+=1
     try:oid=int(h.header.get("OBJ_ID",h.header.get("OBJECT_ID",0)))
     except (ValueError,TypeError):continue
     if oid not in valid.index:continue
     row=valid.loc[oid]
     signal_name=h.name.upper().replace("_META","_COMBINED1D_SIGNAL")
     if signal_name not in hdunames:continue
     signal_hdu=hdus[hdunames[signal_name]]
     cols={x.upper():x for x in signal_hdu.columns.names}
     if not {"WAVELENGTH","SIGNAL","MASK","QUALITY","VAR"}.issubset(cols):continue
     wl=np.asarray(signal_hdu.data[cols["WAVELENGTH"]],dtype=float).reshape(-1)
     flux=np.asarray(signal_hdu.data[cols["SIGNAL"]],dtype=float).reshape(-1)
     mask=np.asarray(signal_hdu.data[cols["MASK"]]).reshape(-1)
     qual=np.asarray(signal_hdu.data[cols["QUALITY"]],dtype=float).reshape(-1)
     var=np.asarray(signal_hdu.data[cols["VAR"]],dtype=float).reshape(-1)
     n=min(map(len,[wl,flux,mask,qual,var]))
     wl,flux,mask,qual,var=(x[:n] for x in [wl,flux,mask,qual,var])
     good=np.isfinite(wl)&np.isfinite(flux)&np.isfinite(var)&(var>0)&(mask==0)&(qual>.8)
     expected=LINE_A*(1+float(row.spe_z))
     in_range=bool(np.nanmin(wl)<expected<np.nanmax(wl))
     match={"object_id":int(oid),"tile":int(tile),"s3_key":obj["Key"],"hdu_signal":signal_name,
            "catalogue_z":float(row.spe_z),"catalogue_Halpha_snr":float(row.ha_snr),
            "catalogue_Halpha_flux":float(row.ha_flux),"expected_line_wavelength_A":float(expected),
            "wavelength_range_A":[float(np.nanmin(wl)),float(np.nanmax(wl))],
            "usable_bins":int(good.sum()),"total_bins":int(n),"Halpha_covered_by_wavelength_range":in_range}
     info["matches"].append(match);REPORT["candidates_found"]+=1
     print("MATCH",match,flush=True)
     if not in_range or good.sum()<20 or REPORT["plotted"]>=3:continue
     near=(np.abs(wl-expected)<330)
     if (near&good).sum()<8:continue
     tbl=pd.DataFrame({"wavelength_A":wl[near],"signal_native":flux[near],"variance_native":var[near],"quality":qual[near],"mask":mask[near],"usable":good[near]})
     tbl.to_csv(OUT/f"nisp_{oid}_line_window.csv",index=False)
     x=wl[near];y=flux[near];goodnear=good[near]
     fig,ax=plt.subplots(figsize=(8.5,3.8))
     ax.plot(x,y,lw=.85,color="0.65",label="Released combined signal")
     ax.plot(x[goodnear],y[goodnear],lw=1.1,color="tab:blue",label="Clean mask & quality>0.8")
     ax.axvline(expected,color="tab:red",ls="--",label="Halpha expected from pipeline z")
     ax.set(xlabel="Observed wavelength (Angstrom)",ylabel="Released signal (native product units)",
            title=f"Actual matched Euclid NISP 1D spectrum: object {oid}")
     ax.legend(fontsize=8);fig.tight_layout()
     fn=f"nisp_{oid}_halpha_window.png"
     fig.savefig(OUT/fn,dpi=180);plt.close(fig)
     REPORT["plots"].append({"filename":fn,"object_id":oid,"relative_path":f"observed_results/matched_spectra/{fn}","s3_key":obj["Key"]})
     REPORT["plotted"]+=1
     if REPORT["plotted"]>=3:break
    info["n_meta_hdus_checked"]=report_meta
   if REPORT["plotted"]>=3:break
  finally:
   os.unlink(local.name)
for tile in [101834044,101834632,101834043]:
 try:
  inspect(tile)
  if REPORT["plotted"]>=3:break
 except Exception as exc:
  REPORT["errors"].append({"tile":tile,"error":str(exc),"traceback":traceback.format_exc()})
  print("ERROR",tile,traceback.format_exc(),flush=True)
 finally:save()
print("MATCHED SPECTRUM AUDIT",json.dumps({"count":REPORT["candidates_found"],"plotted":REPORT["plotted"],"errors":len(REPORT["errors"])},indent=2),flush=True)
