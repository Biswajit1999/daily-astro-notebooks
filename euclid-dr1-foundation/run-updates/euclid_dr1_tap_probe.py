#!/usr/bin/env python3
"""Read-only Euclid DR1-Foundation TAP availability probe. No fabricated rows.

Usage: python euclid_dr1_tap_probe.py --out intake.json
Requires network access to IRSA; Python standard library only.
"""
import argparse
import datetime as dt
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://irsa.ipac.caltech.edu/TAP/sync"
TABLE = "euclid_dr1_mer_catalogue_deep_survey"
# Fixed, preregistered cone; actual DR1 coverage MUST be established by response.
RA, DEC, RADIUS_DEG = 62.5, -48.0, 0.025
QUERIES = {
    "schema": ("SELECT column_name, datatype, unit, description "
               "FROM TAP_SCHEMA.columns WHERE table_name = '" + TABLE + "'"),
    "sample": "SELECT TOP 1 * FROM " + TABLE,
}

def fetch(query, timeout=45):
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL",
                                     "FORMAT": "csv", "QUERY": query})
    request = urllib.request.Request(ENDPOINT + "?" + params,
                                     headers={"User-Agent": "euclid-dr1-foundation-research-probe/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("Response exceeded 2 MB cap")
        return {"http_status": response.status,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body), "body": body.decode("utf-8")}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="intake.json")
    args = parser.parse_args()
    result = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "endpoint": ENDPOINT, "table": TABLE,
              "preregistered_cone_icrs_deg": [RA, DEC, RADIUS_DEG],
              "queries": {}, "status": "blocked"}
    for name, query in QUERIES.items():
        try:
            response = fetch(query)
            result["queries"][name] = {"adql": query, **response}
        except (urllib.error.URLError, TimeoutError, ValueError, UnicodeError) as exc:
            result["queries"][name] = {"adql": query, "error": repr(exc)}
    if all("http_status" in r and r["http_status"] == 200
           and not r["body"].lstrip().startswith("<")
           for r in result["queries"].values()):
        result["status"] = "metadata_retrieved_not_observational_test"
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(result["status"], args.out)

if __name__ == "__main__":
    main()
