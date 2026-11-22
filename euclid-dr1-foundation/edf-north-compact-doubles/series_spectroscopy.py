"""Recheck exact Euclid SIR extractions for an investigated candidate."""
from argparse import ArgumentParser
import gzip
import json
from pathlib import Path

from candidate_series import write
from spectra import lookup, safe, scientific_checks


def run(cache, candidate, output):
    combined = json.loads((cache/"series_catalogues.json").read_text())
    tile = combined[candidate]["euclid"]
    inputs = {"targets":{candidate:{k:tile[k]["rows"] for k in ("MER","SPE")}}}
    work = cache/"lines"
    work.mkdir(exist_ok=True)
    data, manifest = lookup(inputs,work)
    manifest["checks"] = scientific_checks(data,inputs,work)
    output.mkdir(parents=True,exist_ok=True)
    write(output/"spectral_checks.json",manifest)
    (output/"nisp_spectra.json.gz").write_bytes(gzip.compress(
        json.dumps(safe(data),allow_nan=False,separators=(",",":")).encode(),mtime=0))


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,required=True)
    parser.add_argument("--candidate",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.cache,args.candidate,args.output)
