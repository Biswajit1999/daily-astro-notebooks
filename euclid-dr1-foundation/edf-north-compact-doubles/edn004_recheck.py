"""Audit the EDN-004 spectral feature across line widths and grism orientations."""
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path

from astropy.io import fits
import numpy as np

from line_fits import line_check


TARGET_IDS = (2718858072642847858, 2718851317642848846)
CENTRE = 13155.546184870003
WIDTHS = (12., 16., 24.)
REST_LINES = {"Halpha":6564.61, "[O III] 5008":5008.24, "[O II]":3727.42, "Hbeta":4862.68,
              "[O III] 4960":4960.30, "[S II] 6718":6718.29, "[S II] 6733":6732.67}
ALTERNATIVES = {
    "Halpha": ("[O III] 5008", "Hbeta", "[S II] 6718", "[S II] 6733"),
    "[O III] 5008": ("[O III] 4960", "Hbeta", "[O II]", "Halpha"),
    "[O II]": ("Hbeta", "[O III] 5008", "Halpha"),
}


def select_sources(paths, original_metadata, output):
    metadata = json.loads(original_metadata.read_text())
    all_traces = defaultdict(list)
    product_manifest = {Path(row["url"]).name: row for row in metadata["sources"]}
    for filename in paths:
        source = product_manifest[filename.name]
        with filename.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != source["sha256"]:
                raise ValueError(f"Unexpected checksum for {filename}")
        with fits.open(filename, memmap=True) as file:
            grism = file[0].header["LRANGE"]
            prefixes = {h.name.split("_")[0]: int(h.header["OBJ_ID"]) for h in file
                        if h.name.endswith("_META") and h.header.get("OBJ_ID") in TARGET_IDS}
            for h in file:
                if not h.name.endswith("_SIGNAL") or h.name.split("_")[0] not in prefixes:
                    continue
                if h.columns["WAVELENGTH"].unit.lower() != "angstrom":
                    raise ValueError(f"Unexpected wavelength units in {h.name}")
                metadata_token = (str(prefixes[h.name.split("_")[0]]), h.name,
                                  h.header.get("GWA_POS", "") or "")
                values = np.column_stack([h.data[key] for key in ("WAVELENGTH","SIGNAL","VAR","MASK")])
                all_traces[grism].append((metadata_token, values))
    if sum(map(len,all_traces.values())) != 80:
        raise ValueError("Incomplete dither sample.")
    for grism, traces in all_traces.items():
        np.savez_compressed(output/f"edn004_{grism}.npz",
                            meta=np.array([row[0] for row in traces]),
                            end=np.cumsum([len(row[1]) for row in traces]),
                            values=np.concatenate([row[1] for row in traces]))


def load_traces(root):
    for grism in ("BGS", "RGS"):
        with np.load(root/f"edn004_{grism}.npz", allow_pickle=False) as file:
            ranges = np.r_[0, file["end"]]
            for i, (source, hdu, orientation) in enumerate(file["meta"]):
                yield int(source), grism, hdu, orientation, file["values"][ranges[i]:ranges[i+1]]


def check(values, center, width):
    wave, flux, var, mask = values.T
    valid = np.isfinite(wave) & np.isfinite(flux) & np.isfinite(var) & (var > 0) & (mask == 0)
    full = line_check(wave, flux, var, valid, center, width)
    candidates = np.flatnonzero(valid & (np.abs(wave-center) < 30))
    clipped = dict(full)
    if candidates.size > 1:
        brightest = candidates[np.argmax(flux[candidates]/np.sqrt(var[candidates]))]
        valid[brightest] = False
        clipped = line_check(wave, flux, var, valid, center, width)
    return {"width_A":width, "full": full, "clip":clipped}


def summarize(inputs):
    fits_by_exposure, hypotheses = [], []
    for source, grism, hdu, orientation, values in load_traces(inputs):
        fits_by_exposure.append({
            "source":str(source), "grism":grism, "hdu":hdu, "orientation":orientation,
            "coadd":"_COMBINED" in hdu, "fits":[check(values,CENTRE,w) for w in WIDTHS],
        })
        if source == TARGET_IDS[0] and "_COMBINED" in hdu:
            for label, lines in ALTERNATIVES.items():
                redshift = CENTRE/REST_LINES[label]-1
                for name in lines:
                    wavelength = REST_LINES[name]*(1+redshift)
                    hypotheses.append({"hypothesis":label, "z":redshift, "grism":grism, "line":name,
                                       **check(values,wavelength,16)})
    return {"source_line_A":CENTRE, "exposures":fits_by_exposure, "alternative_lines":hypotheses}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--fits", type=Path, nargs="+")
    p.add_argument("--manifest", type=Path)
    args=p.parse_args()
    if args.fits:
        select_sources(args.fits, args.manifest, args.output)
    report = summarize(args.output)
    (args.output/"edn004_recheck.json").write_text(json.dumps(report,indent=2)+"\n")
