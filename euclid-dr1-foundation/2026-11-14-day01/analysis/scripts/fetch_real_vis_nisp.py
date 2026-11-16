"""Retrieve real DR1-Foundation MER morphology, VIS image cutout, and SIR spectrum.
Reads only public mission products; records URLs/keys, data fields and caveats.
No synthetic data and no unverified line identification.
"""
from pathlib import Path
from datetime import datetime, timezone
import tempfile, json, traceback, math
import boto3, numpy as np, pandas as pd
from botocore import UNSIGNED
from botocore.config import Config
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.visualization import ImageNormalize, PercentileInterval, AsinhStretch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"real_media"
OUT.mkdir(parents=True,exist_ok=True)
BUCKET="nasa-irsa-euclid-dr1"
TILE="101834044"
s3=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,connect_timeout=10,read_timeout=80,retries={"max_attempts":3}))
report={"created_utc":datetime.now(timezone.utc).isoformat(),"release":"Euclid DR1-Foundation","tile":TILE,"products":{},"errors":{}}
TARGET={"object_id":2696558115658832112,"ra":269.6558115,"dec":65.8832112,"spe_z":1.037758}
def save():
 (OUT/"real_media_report.json").write_text(json.dumps(report,indent=2,default=str))
def product(prefix,needle):
 o=s3.list_objects_v2(Bucket=BUCKET,Prefix=prefix,MaxKeys=150)
 keys=[v for v in o.get("Contents",[]) if needle in v["Key"] and v["Key"].endswith(".fits")]
 if not keys: raise RuntimeError("No data product for "+prefix+needle)
 obj=sorted(keys,key=lambda x:x["Key"])[0]
 return obj["Key"],obj["Size"]
def download(key):
 p=Path(tempfile.gettempdir())/Path(key).name
 s3.download_file(BUCKET,key,str(p))
 return p
def report_tables(label,needle):
 key,size=product(f"dr1/catalogs/MER_FINAL_CATALOG/{TILE}/",needle)
 report["products"][label]={"key":key,"bytes":size}
 local=download(key)
 with fits.open(local,memmap=True) as hdus:
  info=[]
  for h in hdus:
   if hasattr(h,"columns"):
    cols=list(h.columns.names)
   else: cols=[]
   info.append({"name":str(h.name),"shape":str(getattr(h,"shape",None)),"columns":cols[:350]})
  report["products"][label]["hdus"]=info
  for h in hdus:
   cols=h.columns.names if hasattr(h,"columns") else []
   if not cols:continue
   id_col=next((c for c in cols if c.lower() in ["object_id","objectid","obj_id"]),None)
   if id_col is None:continue
   keys=[c for c in cols if ("kron" in c.lower() or "sersic" in c.lower() or "r50" in c.lower() or "ellipt" in c.lower() or "size" in c.lower() or "flux_vis_2fwhm_aper" in c.lower() or c.lower() in ["flag_vis","det_quality_flag","spurious_prob","vis_det","fluxerr_vis_2fwhm_aper","ra","dec","right_ascension","declination"])]
   report["products"][label]["identifier_column"]=id_col
   report["products"][label]["interesting_columns"]=keys
   if not keys:continue
   ids=np.asarray(h.data[id_col]).astype("int64")
   data={"object_id":ids}
   for k in keys:
    if len(h.data[k].shape)==1:
     data[k.lower()]=np.asarray(h.data[k]).astype("float64")
   if len(data)>1:
    df=pd.DataFrame(data)
    df.to_csv(OUT/(label+"_size_fields.csv.gz"),index=False,compression="gzip")
    report["products"][label]["n_rows"]=len(df)
    report["products"][label]["n_target"]=int(np.sum(ids==TARGET["object_id"]))
    if int(np.sum(ids==TARGET["object_id"])): report["products"][label]["target_values"]=df.loc[df.object_id==TARGET["object_id"]].head(3).to_dict("records")
    print("MER",label,"rows",len(df),"fields",list(df.columns),flush=True)
    break
 local.unlink(missing_ok=True)
def image_cutout():
 key,size=product(f"dr1/MER/{TILE}/VIS/","BGSUB-MOSAIC-VIS")
 report["products"]["vis_mosaic"]={"key":key,"bytes":size}
 raw=s3.get_object(Bucket=BUCKET,Key=key,Range="bytes=0-57599")["Body"].read()
 cards=[raw[i:i+80].decode("ascii",errors="replace") for i in range(0,len(raw),80)]
 end=next(i for i,c in enumerate(cards) if c.startswith("END "))
 hdr=fits.Header.fromstring("".join(cards[:end+1]),sep="")
 if int(hdr.get("NAXIS",0))!=2 or int(hdr.get("BITPIX",0))!=-32:
  raise RuntimeError("Unexpected VIS mosaic layout; safe byte-range extraction withheld")
 nx,ny=int(hdr["NAXIS1"]),int(hdr["NAXIS2"])
 offset=(math.ceil((end+1)*80/2880))*2880
 wcs=WCS(hdr)
 x,y=wcs.world_to_pixel_values(TARGET["ra"],TARGET["dec"])
 x0,y0=round(float(np.asarray(x).item())),round(float(np.asarray(y).item()))
 hsize=100
 if x0<hsize or y0<hsize or x0+hsize>=nx or y0+hsize>=ny:
  raise RuntimeError(f"Source lies outside safe 200x200 cutout range: {(x,y)}")
 start=offset+(y0-hsize)*nx*4
 endbyte=offset+(y0+hsize)*nx*4-1
 block=s3.get_object(Bucket=BUCKET,Key=key,Range=f"bytes={start}-{endbyte}")["Body"].read()
 stripe=np.frombuffer(block,dtype=">f4").reshape((2*hsize,nx))
 stamp=stripe[:,x0-hsize:x0+hsize].astype("float32")
 if stamp.shape!=(200,200): raise RuntimeError("Unexpected stamp dimensions")
 np.save(OUT/"euclid_vis_real_cutout.npy",stamp)
 report["products"]["vis_mosaic"].update({"image_shape":[ny,nx],"naxis1":nx,"bitpix":-32,"bunit":hdr.get("BUNIT"),"source_ra":TARGET["ra"],"source_dec":TARGET["dec"],"source_object_id":TARGET["object_id"],"x_pixel":float(x),"y_pixel":float(y),"cutout_shape":[200,200],"finite_pixels":int(np.isfinite(stamp).sum()),"median_pixel":float(np.nanmedian(stamp)),"wcs_header_digest":{k:hdr.get(k) for k in ["CRVAL1","CRVAL2","CRPIX1","CRPIX2","CTYPE1","CTYPE2","CD1_1","CD1_2","CD2_1","CD2_2"]}})
 f,ax=plt.subplots(figsize=(5.5,5.5))
 good=stamp[np.isfinite(stamp)]
 norm=ImageNormalize(vmin=np.percentile(good,2),vmax=np.percentile(good,99.6),stretch=AsinhStretch(a=.03))
 ax.imshow(stamp,cmap="gray_r",origin="lower",norm=norm,interpolation="nearest")
 ax.axhline(hsize-.5,ls=":",lw=.7,color="tab:red")
 ax.axvline(hsize-.5,ls=":",lw=.7,color="tab:red")
 ax.set(xlabel="VIS mosaic pixel offset (0.1 arcsec/pixel)",ylabel="VIS mosaic pixel offset (0.1 arcsec/pixel)")
 ax.set_title("Actual Euclid VIS 20 arcsec cutout\nDR1-F object "+str(TARGET["object_id"]),fontsize=10)
 ax.set_xticks([0,50,100,150,199],[-100,-50,0,50,99])
 ax.set_yticks([0,50,100,150,199],[-100,-50,0,50,99])
 f.tight_layout();f.savefig(OUT/"euclid_vis_real_cutout.png",dpi=210);plt.close(f)
def spectrum():
 key,size=product(f"dr1/SIR_COMBINED_SPECTRA/{TILE}/","W-COMBSPEC")
 report["products"]["nisp_spectrum"]={"key":key,"bytes":size}
 local=download(key)
 with fits.open(local,memmap=True,lazy_load_hdus=True) as hdus:
  report["products"]["nisp_spectrum"]["n_hdus"]=len(hdus)
  report["products"]["nisp_spectrum"]["first_hdus"]=[{"name":h.name,"columns":list(h.columns.names)[:15] if hasattr(h,"columns") else []} for h in hdus[:10]]
  choices=[]
  for j,h in enumerate(hdus):
   nm=h.name.upper()
   if "COMBINED1D_SIGNAL" not in nm:continue
   try:
    names={k.upper():k for k in h.columns.names}
    if not {"WAVELENGTH","SIGNAL"}.issubset(names):continue
    wl=np.asarray(h.data[names["WAVELENGTH"]],dtype=float).reshape(-1)
    signal=np.asarray(h.data[names["SIGNAL"]],dtype=float).reshape(-1)
    masks=np.asarray(h.data[names["MASK"]]).reshape(-1) if "MASK" in names else np.zeros_like(signal)
    var=np.asarray(h.data[names["VAR"]],dtype=float).reshape(-1) if "VAR" in names else np.full_like(signal,np.nan)
    qual=np.asarray(h.data[names["QUALITY"]],dtype=float).reshape(-1) if "QUALITY" in names else np.full_like(signal,np.nan)
    n=min(len(wl),len(signal),len(masks),len(var))
    good=np.isfinite(wl[:n])&np.isfinite(signal[:n])&(masks[:n]==0)
    if np.isfinite(var[:n]).sum():good&=(var[:n]>0)&np.isfinite(var[:n])
    if good.sum()<50:continue
    pre=hdus[j-1].header if j>0 else {}
    meta=hdus[j-1].header if j>0 else {}
    oid=meta.get("OBJ_ID",meta.get("OBJECTID",meta.get("OBJECT_ID")))
    choices.append((j,oid,wl[:n],signal[:n],var[:n],qual[:n],good))
    if len(choices)>=1:break
   except Exception as exc:
    print("skip spectrum HDU",j,str(exc)[:250],flush=True)
  if not choices:raise RuntimeError("No valid 1D spectrum in first product; need further files/DPDD check")
  j,oid,wl,signal,var,qual,good=choices[0]
  d=pd.DataFrame({"wavelength_angstrom":wl,"signal_native":signal,"variance_native":var,"quality":qual,"usable":good})
  d.to_csv(OUT/"euclid_nisp_real_spectrum.csv",index=False)
  meta_hdu=hdus[j-1]
  report["products"]["nisp_spectrum"].update({"chosen_hdu":j,"chosen_hdu_name":hdus[j].name,"previous_hdu_name":meta_hdu.name,"previous_header_object_id":str(oid),"previous_header_RA":str(meta_hdu.header.get("RA_OBJ")),"previous_header_DEC":str(meta_hdu.header.get("DEC_OBJ")),"wavelength_min":float(np.nanmin(wl)),"wavelength_max":float(np.nanmax(wl)),"usable_bins":int(good.sum()),"total_bins":len(wl),"signal_bunit":str(hdus[j].header.get("BUNIT","DPDD native 1e-16 erg/s/cm2/A"))})
  f,ax=plt.subplots(figsize=(9,3.8))
  ax.plot(wl,signal,color="tab:blue",lw=.9,label="Released combined 1D signal")
  ax.scatter(wl[good],signal[good],color="black",s=3,alpha=.4,label="Unmasked usable samples")
  if np.isfinite(var[good]).any():
   err=np.sqrt(np.maximum(var,0))
   ax.fill_between(wl,signal-err,signal+err,alpha=.18,color="tab:blue",label="Pipeline 1 sigma (native)")
  ax.set(xlabel="Observed wavelength (Angstrom)",ylabel="Signal (Euclid product native units)",title="Real Euclid NISP combined 1D spectrum: tile "+TILE+"; HDU "+str(j))
  ax.legend(loc="best",fontsize=8);f.tight_layout()
  f.savefig(OUT/"euclid_nisp_real_spectrum.png",dpi=200);plt.close(f)
 local.unlink(missing_ok=True)
for label,fun in [("mer_final",lambda:report_tables("mer_final","FINAL-CAT_")),("mer_morph",lambda:report_tables("mer_morph","FINAL-MORPH-CAT_")),("vis_image",image_cutout),("nisp_spectrum",spectrum)]:
 try:
  print("START",label,flush=True);fun();print("OK",label,flush=True)
 except Exception as exc:
  report["errors"][label]={"message":str(exc),"traceback":traceback.format_exc()}
  print("FAILED",label,traceback.format_exc(),flush=True)
 finally:save()
