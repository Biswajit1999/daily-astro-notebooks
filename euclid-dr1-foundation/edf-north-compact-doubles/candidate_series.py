"""Follow up ten previously unmeasured held-out Euclid compact pairs."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import csv
from hashlib import file_digest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from catalogue import extract, stage
from holdout_catalogues import check, desi, gaia, simbad
from holdout_colours import HERE, eclipse_catalogue, fetch_one, rank
from holdout_visits import TOKENS, measure, query
from measure_holdout_colours import RADII, components, contrast, evaluate, psf_metadata, psf_smoothed

PREVIOUS = HERE/"results"/"holdout_colour"/"selection.json"
PARENT = HERE/"results"/"holdout_repeaters.csv"
N_TARGETS = 10
EXPECTED_SIGNS = {"VIS": 1, "J": -1, "H": -1, "i2": 1}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def signature(bands, band, sign):
    return all(sign*(bands.get(band,{}).get(str(r),{}).get("a_minus_b_in_background_mad") or 0.)>5
               for r in RADII)


def choose(cache):
    with PARENT.open() as stream:
        rows = list(csv.DictReader(stream))
    lenses, lens_hash = eclipse_catalogue(cache)
    ordered, _ = rank(rows, lenses)
    done = {v["candidate"] for v in json.loads(PREVIOUS.read_text())["candidates"]}
    selected = [{**row,"programme_rank":i} for i,row in enumerate(ordered,1)
                if row["candidate"] not in done and not row["eclipse_match_within_3arcsec"]][:N_TARGETS]
    if len(selected)!=N_TARGETS:
        raise ValueError("Insufficient unseen candidates under the fixed selection")
    with PARENT.open("rb") as stream:
        parent_hash = file_digest(stream,"sha256").hexdigest()
    return {"parent_sha256":parent_hash,"eclipse_sha256":lens_hash,"eclipse_rows":len(lenses),
            "parent_pairs":len(rows),"eligible_reversals":len(ordered),"candidates":selected}


def individual_photometry(cache, selected):
    raw = evaluate(cache,selected)
    tiles = sorted({row["tile"] for row in selected["candidates"]})
    with ThreadPoolExecutor(max_workers=6) as pool:
        psfs = dict(zip(tiles,pool.map(psf_metadata,tiles)))
    for row in selected["candidates"]:
        label = row["candidate"]
        if label not in raw:
            continue
        info = psfs[row["tile"]]
        with np.load(cache/f"{label}.npz") as images:
            psf_matched = {
                str(width): {band:contrast(psf_smoothed(images[band],meta["central_stamp_fwhm_arcsec"], width),
                                           components(row)) for band,meta in info.items() if band in images}
                for width in (.65,.80)
            }
        raw[label]["psf_metadata"] = info
        raw[label]["smoothed"] = psf_matched
        raw[label]["smoothed_reversal"] = bool(all(
            signature(matched,band,EXPECTED_SIGNS[band]) for matched in psf_matched.values() for band in TOKENS))
        raw[label]["subaru_optical_order"] = signature(raw[label]["bands"],"i2",1)
    return raw


def visit_inputs(target,cache):
    try:
        stacks, inputs = {}, {}
        for camera in ("Vis","Nir"):
            data, inputs[camera] = query(target,camera,cache)
            stacks.update(data)
        shared = sorted((o for o,b in stacks if b=="VIS" and all((o,k) in stacks for k in TOKENS)),
                        key=lambda o:stacks[o,"VIS"]["mjd"])
        chosen = list(dict.fromkeys(shared[i] for i in (0,len(shared)//2,len(shared)-1))) if shared else []
        return {"archive_queries":inputs,"common_visit_ids":shared,"examined_visits":chosen}, stacks
    except Exception as exc:
        return {"error":f"{type(exc).__name__}: {exc}","examined_visits":[]}, {}


def visit_stamps(cache,targets):
    def one(target,visit,band,item):
        try:
            _, row = measure(target,visit,band,item,cache)
            return row
        except Exception as exc:
            return {**item,"error":f"{type(exc).__name__}: {exc}"[:500]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        inputs = list(pool.map(lambda t:visit_inputs(t,cache),targets))
        all_tasks = {}
        output = {}
        for target,(meta,stacks) in zip(targets,inputs,strict=True):
            label = target["candidate"]
            output[label] = meta
            all_tasks[label] = {visit:{b:pool.submit(one,target,visit,b,stacks[visit,b]) for b in TOKENS}
                                for visit in meta["examined_visits"]}
        for label,jobs in all_tasks.items():
            visits = {v:{b:f.result() for b,f in task.items()} for v,task in jobs.items()}
            for data in visits.values():
                aper = {b:r.get("apertures",{}) for b,r in data.items()}
                data["reversal_at_all_apertures"] = all(signature(aper,b,EXPECTED_SIGNS[b]) for b in TOKENS)
            output[label]["visits"] = visits
            output[label]["passing_visits"] = [v for v,data in visits.items() if data["reversal_at_all_apertures"]]
            print(label,"visits",len(visits),"passes",len(output[label]["passing_visits"]),flush=True)
    return output


def euclid_table(targets, tile, cache):
    subset = [{**r,"id":r["candidate"]} for r in targets if r["tile"] == tile]
    out = {r["id"]:{} for r in subset}
    available = {}
    for kind in ("MER","SPE","PHZ"):
        try:
            with TemporaryDirectory(dir=cache, prefix=f"tile-{tile}-") as scratch:
                path, source = stage(kind,tile,Path(scratch))
                fields, _ = extract(path,kind,tile,subset,available)
            if kind=="MER":
                available = fields
            for row in subset:
                name = row["id"]
                out[name][kind] = {"input":source,"rows":fields.get(name,[])}
        except Exception as exc:
            for row in subset:
                out[row["id"]][kind] = {"error":f"{type(exc).__name__}: {exc}"[:500]}
        print(tile,kind,{k:len(v[kind].get("rows",[])) for k,v in out.items()},flush=True)
    return out


def catalogues(cache,targets):
    tiles = sorted({row["tile"] for row in targets})
    result = {r["candidate"]:{} for r in targets}
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending = {}
        for row in targets:
            label = row["candidate"]
            root = cache/label
            root.mkdir(exist_ok=True)
            pending[label] = {fn.__name__:pool.submit(check,fn,row,root) for fn in (gaia,simbad,desi)}
        tables = [pool.submit(euclid_table,targets,tile,cache) for tile in tiles]
        for label,requests in pending.items():
            result[label]["external"] = {name:f.result() for name,f in requests.items()}
        for f in tables:
            for label,rows in f.result().items():
                result[label]["euclid"] = rows
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    candidates = choose(cache)
    targets = candidates["candidates"]
    write(cache/"series_selection.json",candidates)
    with ThreadPoolExecutor(max_workers=2) as independent:
        visit_future = independent.submit(visit_stamps,cache,targets)
        catalogue_future = independent.submit(catalogues,cache,targets)
        with ThreadPoolExecutor(max_workers=7) as image_pool:
            candidates["mosaics"] = dict(image_pool.map(lambda r:fetch_one(r,cache),targets))
        write(cache/"series_selection.json",candidates)
        write(cache/"series_photometry.json",individual_photometry(cache,candidates))
        write(cache/"series_visits.json",visit_future.result())
        write(cache/"series_catalogues.json",catalogue_future.result())


if __name__ == "__main__":
    main()
