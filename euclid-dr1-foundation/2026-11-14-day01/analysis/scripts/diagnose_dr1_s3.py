"""Inventory small slices of public Euclid DR1-Foundation S3 bucket."""
import boto3, json, pathlib
from datetime import datetime,timezone
from botocore import UNSIGNED
from botocore.config import Config
bucket="nasa-irsa-euclid-dr1"
s3=boto3.client("s3",region_name="us-east-1",config=Config(signature_version=UNSIGNED,connect_timeout=10,read_timeout=15,retries={"max_attempts":2}))
result={"bucket":bucket,"time_utc":datetime.now(timezone.utc).isoformat(),"probes":[]}
for prefix in ["contributed/dr1/hats/reformatted_catalogs/","contributed/dr1/hats/reformatted_catalogs/euclid_dr1_mer_catalogue_deep_survey/","contributed/dr1/hats/reformatted_catalogs/euclid_dr1_spectro_z_spe_galaxy_candidates_deep/","contributed/dr1/hats/reformatted_catalogs/euclid_dr1_spectro_line_features_spe_line_features_deep/"]:
 try:
  o=s3.list_objects_v2(Bucket=bucket,Prefix=prefix,Delimiter="/",MaxKeys=50)
  record={"prefix":prefix,"subdirs":[v["Prefix"] for v in o.get("CommonPrefixes",[])],"objects":[{"key":v["Key"],"size":v["Size"]} for v in o.get("Contents",[])][:30],"is_truncated":o.get("IsTruncated",False)}
  result["probes"].append(record)
  print("PREFIX",prefix,"SUBDIRS",record["subdirs"],"OBJECTS",record["objects"][:12],flush=True)
 except Exception as exc: result["probes"].append({"prefix":prefix,"error":str(exc)});print("ERROR",prefix,str(exc),flush=True)
p=pathlib.Path(__file__).resolve().parents[1]/"metadata"/"s3_inventory.json"
p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2))
