"""Test the leading held-out candidate on separated full-visit VIS and NISP stacks."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
from pathlib import Path
from urllib.parse import urlencode

from astropy.io.votable import parse_single_table

from archive import BUCKET, get, image_hdu
from holdout_colours import register
from measure_holdout_colours import components, contrast

SIA = "https://irsa.ipac.caltech.edu/SIA"
TOKENS = {"VIS": "VIS_SWL-STK-", "J": "STK-IMAGE_J-", "H": "STK-IMAGE_H-"}


def query(target, name, cache):
    collection = f"euclid_dr1_Dpd{name}StackedFrame"
    url = SIA+"?"+urlencode({"POS": f'CIRCLE {target["ra"]} {target["dec"]} 0.006',
                             "COLLECTION": collection, "MAXREC": 150})
    path = cache/f"{target['candidate']}-{name}-sia.xml"
    if not path.exists():
        path.write_bytes(get(url, 34))
    raw = path.read_bytes()
    table = parse_single_table(io.BytesIO(raw))
    fields = {field.name: i for i, field in enumerate(table.fields)}
    result = {}
    for row in table.array:
        access = str(row[fields["access_url"]])
        for band, token in TOKENS.items():
            if token in access:
                obs = str(row[fields["obs_id"]]).split("_")[0]
                key = json.loads(str(row[fields["cloud_access"]]))["aws"]["key"]
                result[(obs, band)] = {"mjd": float(row[fields["t_min"]]), "url": f"{BUCKET}/{key}"}
    return result, {"url": url, "sha256": sha256(raw).hexdigest(), "table_rows": len(table.array)}


def measure(target, visit, band, item, cache):
    image, meta = register(target, image_hdu(item["url"]))
    metric = contrast(image, components(target))
    path = cache/f"{target['candidate']}-{visit}-{band}.npy"
    import numpy as np
    np.save(path, image)
    return band, dict(item, **{k:v for k,v in meta.items() if k != "url"}, apertures=metric)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    p = args.cache
    target = json.loads((p/"selection.json").read_text())["candidates"][0]
    stacks, inputs = {}, {}
    for name in ("Vis", "Nir"):
        obs, inputs[name] = query(target, name, p)
        stacks.update(obs)
    shared = sorted((o for o, b in stacks if b == "VIS" and all((o, k) in stacks for k in TOKENS)),
                    key=lambda o: stacks[o,"VIS"]["mjd"])
    if len(shared) < 3:
        raise ValueError("Fewer than three common VIS/J/H visits")
    visits = [shared[i] for i in (0,len(shared)//2,len(shared)-1)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {v: [pool.submit(measure,target,v,b,stacks[v,b],p) for b in TOKENS] for v in visits}
        observations = {v: dict(f.result() for f in work) for v, work in jobs.items()}
    (p/"visit_checks.json").write_text(json.dumps({"candidate": target["candidate"], "catalogue_queries":inputs,
                                                   "n_common_visits":len(shared), "visits":observations},
                                                  indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
