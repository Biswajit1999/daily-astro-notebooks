"""Download and verify the public inputs for the dark-universe notebook."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

from get_arc_fits import BANDS

DESI="https://raw.githubusercontent.com/CobayaSampler/bao_data/bb0c1c9009dc76d1391300e169e8df38fd1096db/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_"
ZENODO="https://zenodo.org/records/19654904/files/"
INPUTS={
    "bao_mean.txt":(DESI+"mean.txt","9ac154ab583ce759c0f7eef3c978c7c70a6ead2d18774caceadf1a350a640585"),
    "bao_cov.txt":(DESI+"cov.txt","252a143274c8a07c78694c119617d36594f6d7965d00319ca611c6ffb886e509"),
    "eclipse_object.zip":(ZENODO+"ECLIPSE_object_catalogue.zip?download=1","5486e82867a0209767d542478b5375413f68bc8adf033f157da940b4c6f75438"),
    "eclipse_physical.zip":(ZENODO+"ECLIPSE_D_dr1_redshifts_and_physical_properties.zip?download=1","511b68d3aa00c2289098fe47e251b3e9667fc6ea025083396a9a9ebcda8fb186"),
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def prepare(folder):
    folder.mkdir(parents=True,exist_ok=True)
    def retrieve(item):
        name,(url,sha)=item
        path=folder/name
        if not path.exists():
            temp=path.with_suffix(".part")
            with urlopen(url,timeout=60) as source, temp.open("wb") as dest:
                shutil.copyfileobj(source,dest)
            if digest(temp)!=sha:
                raise ValueError(f"Checksum mismatch for downloaded {name}")
            temp.replace(path)
        elif digest(path)!=sha:
            raise ValueError(f"Checksum mismatch for cached {name}")
        return {"filename":name,"public_url":url,"sha256":sha,"bytes":path.stat().st_size}
    with ThreadPoolExecutor(4) as pool:
        rows=list(pool.map(retrieve,INPUTS.items()))
    (folder/"public_sources.json").write_text(json.dumps(rows,indent=2)+"\n")
    bands=[folder/f"arc_{b}.fits" for b in BANDS]
    if not (folder/"arc_image_manifest.json").is_file() or not all(p.is_file() for p in bands):
        subprocess.run([sys.executable,str(Path(__file__).with_name("get_arc_fits.py")),str(folder)],check=True)
    return rows


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs",type=Path)
    args=p.parse_args()
    for row in prepare(args.inputs):
        print(row["filename"],row["bytes"],row["sha256"])
