"""Cross-match the EDF-N pilot against public DESI DR1 spectroscopy."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np
import pandas as pd

from audit_grism_halpha import DAY02, load_matches

ENDPOINT = "https://datalab.noirlab.edu/tap/sync"
QUERY = """SELECT targetid, mean_fiber_ra, mean_fiber_dec, z, zerr, zwarn, spectype, zcat_primary
FROM desi_dr1.zpix
WHERE zwarn = 0
AND mean_fiber_ra BETWEEN 269.02 AND 270.45
AND mean_fiber_dec BETWEEN 65.738 AND 66.298"""
MAXREC = 50000


def read_desi(cache):
    if not cache.exists():
        params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                  "QUERY": QUERY, "MAXREC": MAXREC}
        with urlopen(ENDPOINT + "?" + urlencode(params), timeout=120) as response:
            raw = response.read()
        if not raw.lower().startswith(b"targetid,"):
            raise ValueError("DESI TAP did not return a CSV table")
        cache.parent.mkdir(parents=True, exist_ok=True)
        temp = cache.with_suffix(".tmp")
        temp.write_bytes(raw)
        temp.replace(cache)
    data = pd.read_csv(cache)
    if len(data) >= MAXREC:
        raise ValueError("DESI response may be truncated")
    primary = data.zcat_primary.astype(str).str.lower().isin(("t", "true", "1"))
    catalogue = data[primary & data.zwarn.eq(0) & np.isfinite(data.z)].copy()
    if not catalogue.targetid.is_unique:
        raise ValueError("Duplicate primary DESI target IDs")
    return data, catalogue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desi-cache", type=Path, required=True)
    args = parser.parse_args()
    raw, desi = read_desi(args.desi_cache)
    pilot = pd.read_csv(DAY02 / "observed_results" / "all_morphology_matched.csv.gz")
    euclid_coord = SkyCoord(pilot.ra.to_numpy() * u.deg, pilot.dec.to_numpy() * u.deg)
    desi_coord = SkyCoord(desi.mean_fiber_ra.to_numpy() * u.deg, desi.mean_fiber_dec.to_numpy() * u.deg)
    # Find all pairs within 1 arcsec, then reject multiply matched IDs on either side.
    a, b, separation, _ = desi_coord.search_around_sky(euclid_coord, 1 * u.arcsec)
    pair = pilot.iloc[a][["object_id", "spe_z", "clean"]].reset_index(drop=True)
    rhs = desi.iloc[b][["targetid", "z", "zerr", "spectype"]].reset_index(drop=True)
    pair = pd.concat([pair, rhs], axis=1).assign(separation_arcsec=separation.arcsec)
    pair["delta_z_norm"] = (pair.spe_z - pair.z) / (1 + pair.z)
    pair = pair.sort_values(["object_id", "separation_arcsec"])
    outputs = {}
    for radius in (0.2, 0.5, 1.0):
        subset = pair[pair.separation_arcsec.le(radius)]
        unique = subset[~subset.object_id.duplicated(keep=False) & ~subset.targetid.duplicated(keep=False)]
        outputs[str(radius)] = {"pairs": len(subset), "one_to_one": len(unique)}
        for label, group in (("all", unique), ("strict_imaging", unique[unique.clean])):
            agreement = group.delta_z_norm.abs().le(0.002)
            outputs[str(radius)][label] = {
                "n": len(group), "consistent": int(agreement.sum()),
                "desi_types": group.spectype.value_counts().to_dict(),
            }
    spectrum_ids = {r["object_id"] for r in load_matches()}
    result = {
        "endpoint": ENDPOINT, "query": QUERY,
        "raw_csv_sha256": hashlib.sha256(args.desi_cache.read_bytes()).hexdigest(),
        "desi_box_rows": len(raw), "desi_primary_good_rows": len(desi),
        "agreement_threshold_abs_delta_z_over_1_plus_zdesi": 0.002,
        "match_radii_arcsec": outputs,
        "dither_audit_objects_within_1_arcsec": sorted(
            str(oid) for oid in set(pair.object_id) & spectrum_ids
        ),
    }
    output = DAY02 / "validation"
    pair.to_csv(output / "desi_pairs.csv", index=False, float_format="%.12g")
    (output / "desi_redshift_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
