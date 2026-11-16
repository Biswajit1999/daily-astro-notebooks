"""Probe real DR1-F SIR/VIS products for EDF-N tile 101834044."""
import boto3, json
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from datetime import datetime,timezone
B="nasa-irsa-euclid-dr1"
s=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,connect_timeout=10,read_timeout=30))
P=Path(__file__).resolve().parents[1]/"pilot_real";P.mkdir(parents=True,exist_ok=True)
o={"time":datetime.now(timezone.utc).isoformat(),"tile":101834044,"products":[]}
for prefix in ["dr1/SIR_COMBINED_SPECTRA/101834044/","dr1/MER/101834044/VIS/","dr1/catalogs/MER_FINAL_CATALOG/101834044/","dr1/catalogs/SPE_PF_OUTPUT_CATALOG/101834044/"]:
 items=s.list_objects_v2(Bucket=B,Prefix=prefix,MaxKeys=100)
 found=[]
 for obj in items.get("Contents",[]):
  key=obj["Key"]
  if key.endswith(".fits"):
   val={"key":key,"size":obj["Size"]}
   if "BGSUB-MOSAIC" in key or "W-COMBSPEC" in key:
    try:
     b=s.get_object(Bucket=B,Key=key,Range="bytes=0-2879")["Body"].read()
     val["first_cards"]=[b[i:i+80].decode("ascii",errors="replace").strip() for i in range(0,2880,80)][:28]
    except Exception as exc: val["header_error"]=str(exc)
   found.append(val)
 o["products"].append({"prefix":prefix,"count_first_page":len(found),"truncated":items.get("IsTruncated"),"files":found[:20]})
 print(prefix,len(found),flush=True)
 for f in found[:6]:
  print("FILE",f["key"],f["size"],flush=True)
  for c in f.get("first_cards",[])[:15]: print(c,flush=True)
(P/"real_media_inventory.json").write_text(json.dumps(o,indent=2))
