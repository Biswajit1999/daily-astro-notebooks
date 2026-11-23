#!/usr/bin/env python3
"""Fail-closed Euclid DR1-F deep-visit schema and bounded-data intake.
Only the public IRSA TAP endpoint is queried. No simulated observations.
"""
import argparse, csv, datetime, hashlib, io, json, urllib.parse, urllib.request

ENDPOINT="https://irsa.ipac.caltech.edu/TAP/sync"
TABLE="euclid_dr1_mer_catalogue_deep_mode"
PHOT="euclid_dr1_mer_catalogue_deep_mode_photometry"
MAX_BYTES=4_000_000

def query(adql, timeout):
    params=urllib.parse.urlencode(dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=adql))
    req=urllib.request.Request(ENDPOINT+"?"+params,headers={"User-Agent":"Biswajit-Jana-Euclid-DR1-Foundation/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        body=resp.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES: raise ValueError("response over byte cap")
        if resp.status!=200: raise ValueError("HTTP "+str(resp.status))
    txt=body.decode("utf-8")
    if txt.lstrip().startswith("<"): raise ValueError("TAP XML/error response, not CSV")
    rows=list(csv.DictReader(io.StringIO(txt)))
    if not rows and not txt.strip(): raise ValueError("empty TAP response")
    return {"sha256":hashlib.sha256(body).hexdigest(),"bytes":len(body),
            "row_count":len(rows),"columns":list(rows[0]) if rows else list(next(csv.reader(io.StringIO(txt)))),"rows":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="deep_visit_intake.json")
    p.add_argument("--timeout",type=int,default=20)
    a=p.parse_args()
    tasks={
      "deep_visit_schema": "SELECT column_name, datatype, unit, description FROM TAP_SCHEMA.columns WHERE table_name = '"+TABLE+"'",
      "deep_visit_photometry_schema": "SELECT column_name, datatype, unit, description FROM TAP_SCHEMA.columns WHERE table_name = '"+PHOT+"'",
      "deep_visit_preview": "SELECT TOP 5 * FROM "+TABLE,
    }
    record={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "endpoint":ENDPOINT,"tables":[TABLE,PHOT],"status":"blocked",
      "scope":"schema/preview only; no object variability test", "tasks":{}}
    for name,adql in tasks.items():
        try: record["tasks"][name]={"adql":adql,**query(adql,a.timeout)}
        except Exception as exc: record["tasks"][name]={"adql":adql,"error_type":type(exc).__name__,"error":str(exc)}
    if all("sha256" in x for x in record["tasks"].values()):
        record["status"]="schema_available_observational_test_not_run"
    with open(a.out,"w",encoding="utf-8") as f:json.dump(record,f,indent=2)
    print(record["status"],a.out)
if __name__=="__main__":main()
