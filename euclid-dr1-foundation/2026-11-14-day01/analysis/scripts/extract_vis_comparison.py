"""Extract WCS-registered Euclid DR1-F VIS comparison stamps; no simulations."""
from pathlib import Path
import json,math
import boto3, numpy as np
from botocore import UNSIGNED
from botocore.config import Config
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import ImageNormalize, AsinhStretch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B="nasa-irsa-euclid-dr1"
KEY="dr1/MER/101834044/VIS/EUC_MER_BGSUB-MOSAIC-VIS_TILE101834044-F20EA5_20250828T043943.523084Z_00.00.fits"
s=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,read_timeout=50))
raw=s.get_object(Bucket=B,Key=KEY,Range="bytes=0-57599")["Body"].read()
c=[raw[i:i+80].decode("ascii",errors="replace") for i in range(0,len(raw),80)]
end=next(i for i,v in enumerate(c) if v.startswith("END "))
h=fits.Header.fromstring("".join(c[:end+1]),sep="")
w=WCS(h); nx=int(h["NAXIS1"]);off=math.ceil((end+1)*80/2880)*2880
targets=[
 {"id":2697974927659867240,"ra":269.7974927,"dec":65.9867240,"flag_vis":0,"det_quality_flag":0,"ha_snr":36.576805,"z":1.393485,"label":"Clean control"},
 {"id":2696558115658832112,"ra":269.6558115,"dec":65.8832112,"flag_vis":2,"det_quality_flag":2,"ha_snr":58.615524,"z":1.037758,"label":"Blended control"}]
out=Path(__file__).resolve().parents[1]/"real_media"
out.mkdir(parents=True,exist_ok=True)
stamps=[]
for v in targets:
 x,y=w.world_to_pixel_values(v["ra"],v["dec"])
 cx,cy=int(round(float(np.asarray(x).item()))),int(round(float(np.asarray(y).item())))
 half=100
 start=off+(cy-half)*nx*4;stop=off+(cy+half)*nx*4-1
 raw=s.get_object(Bucket=B,Key=KEY,Range=f"bytes={start}-{stop}")["Body"].read()
 a=np.frombuffer(raw,dtype=">f4").reshape((half*2,nx))[:,cx-half:cx+half].copy().astype('float32')
 np.save(out/f"vis_cutout_{v['id']}.npy",a)
 v["mosaic_x"]=float(x);v["mosaic_y"]=float(y)
 v["finite_pixels"]=int(np.isfinite(a).sum())
 stamps.append(a)
 print(v,flush=True)
fig,axs=plt.subplots(1,2,figsize=(10,5))
for v,a,ax in zip(targets,stamps,axs):
 good=a[np.isfinite(a)]
 lo,hi=np.percentile(good,[2,99.6])
 norm=ImageNormalize(vmin=lo,vmax=hi,stretch=AsinhStretch(a=.03))
 ax.imshow(a,cmap="gray_r",origin="lower",norm=norm,interpolation="nearest")
 ax.plot([99.5],[99.5],"r+",ms=11,mew=1.3)
 ax.set(title=f"{v['label']}  FLAG_VIS={v['flag_vis']}\nDR1-F object {v['id']}",xlabel="VIS pixel offset (0.1 arcsec/px)")
 ax.set_xticks([0,50,100,150,199],[-100,-50,0,50,99])
 ax.set_yticks([0,50,100,150,199],[-100,-50,0,50,99])
axs[0].set_ylabel("VIS pixel offset (0.1 arcsec/px)")
fig.suptitle("Observed VIS mosaic cutouts: visually inspect contamination before statistics",fontsize=11)
fig.tight_layout()
fig.savefig(out/"euclid_vis_clean_vs_blended_real.png",dpi=210)
plt.close(fig)
(out/"cutout_sources.json").write_text(json.dumps({"s3_key":KEY,"targets":targets},indent=2))
