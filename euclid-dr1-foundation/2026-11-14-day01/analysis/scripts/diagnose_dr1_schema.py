"""Diagnostic-only inspection of current Euclid DR1-Foundation TAP deployment."""
import json
import pathlib
import requests
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"metadata"/"live_irsa_schema_diagnostic.json"
ENDPOINTS=["https://irsa.ipac.caltech.edu/TAP/sync","https://irsa.ipac.caltech.edu/TAP/capabilities"]
NAMES=["euclid_dr1_mer_catalogue_deep_survey","euclid_dr1_spectro_z_spe_galaxy_candidates_deep","euclid_dr1_spectro_line_features_spe_line_features_deep"]
s=requests.Session()
result={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"base_url":ENDPOINTS[0],"checks":[]}
def call(label,query):
 try:
  r=s.get(ENDPOINTS[0],params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":query},timeout=100)
  result["checks"].append({"label":label,"http_code":r.status_code,"content_type":r.headers.get("content-type"),"sample":r.text[:12500]})
  print("---",label,r.status_code,r.headers.get("content-type"))
  print(r.text[:12500])
 except Exception as exc:
  result["checks"].append({"label":label,"error":str(exc)})
  print("---",label,"ERROR",repr(exc))
for uri in ENDPOINTS:
 try:
  r=s.get(uri,timeout=25)
  print("ENDPOINT",uri,r.status_code,r.headers.get("content-type"),r.text[:250])
 except Exception as exc: print("ENDPOINT ERROR",uri,str(exc))
call("tables","SELECT TOP 40 table_name FROM TAP_SCHEMA.tables WHERE table_name LIKE 'euclid_dr1%'")
for name in NAMES:
 call("schema_"+name,"SELECT TOP 90 column_name, unit, datatype, description FROM TAP_SCHEMA.columns WHERE table_name = '"+name+"'")
 call("row_"+name,"SELECT TOP 1 * FROM "+name)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,indent=2))
print("WROTE",OUT)
