"""Match external cluster spectroscopy and Euclid DR1-Foundation photometry."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

import astropy.units as u
from astropy.coordinates import SkyCoord, concatenate
from astropy.io import fits
from astropy.table import Table
import numpy as np
from mocpy import MOC

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "act-cluster-colour"))
from measure_colour import HEALPIX, PRIMARY, angular_grid, flux, mask_at, samples, wilson

C_KMS = 299792.458
WINDOW = 2500
MATCH_ARCSEC = 0.8
COLOUR_BANDS = {"VIS": "VIS", "DECAM_r": "R_EXT_DECAM", "DECAM_i": "I_EXT_DECAM", "NIR_J": "J"}


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        part = path.with_suffix(".part")
        with urlopen(url, timeout=120) as src, part.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        part.replace(path)
    with path.open("rb") as handle:
        return path, file_digest(handle, "sha256").hexdigest()


def read_tables(path):
    document = path.read_text()
    if "Error=" in document or "#RESOURCE" not in document:
        raise ValueError(f"Invalid VizieR response in {path}")
    tables = {}
    for block in document.split("#Table")[1:]:
        lines = block.splitlines()[1:]
        table = next((row.split(": ", 1)[1] for row in lines if row.startswith("#Name: ")), None)
        if table is None:
            continue
        data = [row for row in lines if row.strip() and not row.startswith("#")]
        if not data:
            tables[table] = []
            continue
        columns = data[0].split("\t")
        rows = []
        for values in data[3:]:
            parts = [cell.strip() for cell in values.split("\t")]
            if len(parts) != len(columns):
                raise ValueError(f"Malformed VizieR row in {table}")
            rows.append(dict(zip(columns, parts, strict=True)))
        tables[table] = rows
    if not tables:
        raise ValueError(f"No VizieR table metadata returned in {path}")
    return tables


def coordinates(records, ra_unit=u.deg):
    return SkyCoord([r["RAJ2000"] for r in records], [r["DEJ2000"] for r in records],
                    unit=(ra_unit, u.deg))


def redshift_velocity(redshift, systemic):
    return C_KMS * (np.asarray(redshift) - systemic) / (1 + systemic)


def in_aperture(spectra, centre, theta, systemic):
    if not spectra:
        return []
    positions = coordinates(spectra)
    radius = centre.separation(positions).arcmin / theta
    velocity = redshift_velocity([float(r["z"]) for r in spectra], systemic)
    return [
        dict(row, r_over_r500=float(r), dv_kms=float(v))
        for row, r, v in zip(spectra, radius, velocity, strict=True) if r < 2
    ]


def distance_match(act, gmos, moc):
    observations = gmos["J/ApJS/227/3/table1"]
    systemic = {r["SPT-CL"]: float(r["z"]) for r in gmos["J/ApJS/227/3/table2"]}
    centres = {r["SPT-CL"]: r for r in observations if r["SPT-CL"] in systemic}
    spectro = defaultdict(dict)
    for row in gmos["J/ApJS/227/3/table3"]:
        if row["z"] and float(row["z"]) > 0:
            previous = spectro[row["SPT-CL"]].get(row["File"])
            if previous is None or float(row["e_z"]) < float(previous["e_z"]):
                spectro[row["SPT-CL"]][row["File"]] = row
    act_sky = SkyCoord(act["RADeg"], act["decDeg"], unit=u.deg)
    obs_sky = coordinates(list(centres.values()), u.hourangle)
    indices, offsets, _ = obs_sky.match_to_catalog_sky(act_sky)
    result = {}
    candidates = {}
    counters = {"gmos_systemic_redshift_count": len(centres), "act_matches": 0, "mer_centres": 0}
    for name, index, offset in zip(centres, indices, offsets, strict=True):
        row, centre, z = act[index], act_sky[index], systemic[name]
        if offset.arcmin > 2 or abs(float(row["redshift"]) - z) / (1 + z) > .05:
            continue
        counters["act_matches"] += 1
        if not moc.contains_skycoords(centre):
            continue
        counters["mer_centres"] += 1
        key = str(row["name"])
        if key in result:
            raise ValueError(f"Two SPT-GMOS cluster centres match {key}")
        theta = float(row["theta500Arcmin"])
        seen = in_aperture(list(spectro[name].values()), centre, theta, z)
        member = [r for r in seen if abs(r["dv_kms"]) <= WINDOW]
        outer = [r for r in member if r["r_over_r500"] >= 1]
        on_map = moc.contains_skycoords(coordinates(outer)) if outer else []
        result[key] = {
            "act_name": key, "spt_name": name, "spt_redshift": z, "centre_offset_arcmin": float(offset.arcmin),
            "ra_deg": float(centre.ra.deg), "dec_deg": float(centre.dec.deg), "theta500_arcmin": theta,
            "core_candidates": len(member) - len(outer), "outskirts_candidates": len(outer),
            "outskirts_inside_mer_geometric_footprint": int(np.count_nonzero(on_map)),
            "outskirts_candidates_1500_kms": sum(abs(r["dv_kms"]) <= 1500 for r in outer),
        }
        candidates[key] = {"outskirts": outer, "core": [r for r in seen if r["r_over_r500"] < 1]}
    return counters, sorted(result.values(), key=lambda r: (-r["outskirts_candidates"], r["act_name"])), candidates


def check_pilot(clusters, act, tables, ru, gm):
    reports = []
    all_act = {r["name"]: r for r in act}
    for c in clusters:
        name = c["name"].split()[1]
        centre = SkyCoord(c["ra_deg"], c["dec_deg"], unit=u.deg)
        r, z = c["theta500_arcmin"], c["redshift"]
        by = tables[name]
        ozdes = by["ozdes"]["J/MNRAS/496/19/ozdesdr2"]
        six = by["6dfgs"]["VII/259/6dfgs"]
        oss = [row for row in ozdes if row["q_z"] in ("3", "4") and float(row["z"]) > 0]
        ss = [dict(row, z=str(float(row["cz"]) / C_KMS)) for row in six
              if row["q_cz"] in ("3", "4") and float(row["cz"]) > 0]
        sixth = []
        if ss:
            sky = coordinates(ss, u.hourangle)
            for row, radius in zip(ss, centre.separation(sky).arcmin / r, strict=True):
                if radius < 2 and abs(redshift_velocity(float(row["z"]), z)) <= WINDOW:
                    sixth.append(row)
        erass = next(iter(by["erass_opt"].values()))
        counterparts = [
            {"name": o["Name"], "offset_arcmin": float(o["_r"]), "best_z": float(o["Bestz"]),
             "best_z_type": o["Bestztype"]}
            for o in erass if float(o["_r"]) <= 2 and o["Bestz"]
        ]
        reports.append({
            "name": c["name"], "act_redshift": z, "act_redshift_type": str(all_act[c["name"]]["redshiftType"]),
            "act_redshift_source": str(all_act[c["name"]]["redshiftSource"]),
            "ozdes_cone_rows": len(ozdes), "6dfgs_cone_rows": len(six),
            "6dfgs_row_quality_flags": [row["q_cz"] for row in six],
            "gmos_within_2r500": len(in_aperture(gm, centre, r, z)),
            "ruel_within_2r500": len(in_aperture(ru, centre, r, z)),
            "ozdes_redshift_window_candidates_within_2r500": sum(
                abs(s["dv_kms"]) <= WINDOW for s in in_aperture(oss, centre, r, z)),
            "6dfgs_redshift_window_candidates_within_2r500": len(sixth),
            "erass1_optical_counterparts_within_2arcmin": counterparts,
        })
    return reports


def tile_match(sky, tile, files, *, record_weights=False):
    """Find all possible MER counterparts, preserving ambiguity across tiles."""
    with fits.open(files["MER"], memmap=True) as hdus:
        data = hdus[1].data
        sources = SkyCoord(data["RIGHT_ASCENSION"], data["DECLINATION"], unit=u.deg)
        query, found, sep, _ = sources.search_around_sky(sky, MATCH_ARCSEC * u.arcsec)
        selected = data[found]
        assert np.all(selected["TILE_INDEX"] == tile)
        ids = selected["OBJECT_ID"].astype(np.int64)
        values = {band: flux(selected, code) for band, code in COLOUR_BANDS.items()}
        good_shape = ((selected["VIS_DET"] == 1) & (selected["SPURIOUS_FLAG"] == 0)
                      & (selected["POINT_LIKE_FLAG"] != 1))
        detection_flag = selected["DET_QUALITY_FLAG"].astype(int)
    cells = HEALPIX.lonlat_to_healpix(sources[found].ra, sources[found].dec)
    masks = {band: mask_at(files[band], tile, band, cells) for band in COLOUR_BANDS}
    limit, imag_limit, cutoff = PRIMARY
    result = []
    for k, (j, separation) in enumerate(zip(query, sep, strict=True)):
        r, i = values["DECAM_r"][0][k], values["DECAM_i"][0][k]
        ok_flux = all(values[band][1][k] for band in ("VIS", "DECAM_r", "DECAM_i"))
        valid_colour = bool(ok_flux and good_shape[k])
        im = float(23.9 - 2.5 * np.log10(i)) if valid_colour else None
        colour = float(-2.5 * np.log10(r / i)) if valid_colour else None
        optical_aperture = bool(valid_colour and im <= imag_limit and
                                all(masks[b][k] >= limit for b in ("VIS", "DECAM_r", "DECAM_i")))
        optical = bool(optical_aperture and detection_flag[k] == 0)
        allow_extended = bool(optical_aperture and (detection_flag[k] & ~512) == 0)
        common = optical and bool(masks["NIR_J"][k] >= limit)
        match = {
            "tile": tile, "object_id": int(ids[k]), "separation_arcsec": float(separation.arcsec),
            "i_ab": im, "r_minus_i_ab": colour, "red_colour": colour >= cutoff if valid_colour else None,
            "detection_quality_flag": int(detection_flag[k]),
            "optical": bool(optical), "common_footprint": common,
            "optical_allow_extended_area": bool(allow_extended),
            "common_allow_extended_area": bool(allow_extended and masks["NIR_J"][k] >= limit),
            "j_detection": common and bool(values["NIR_J"][1][k]),
        }
        if record_weights:
            match["coverage_weights"] = {
                band: float(weights[k]) if np.isfinite(weights[k]) else None
                for band, weights in masks.items()
            }
        result.append((int(j), match))
    return result


def joint_area(field, paths):
    ra, dec, theta = [field[k] for k in ("ra_deg", "dec_deg", "theta500_arcmin")]
    lon, lat = angular_grid(np.radians([ra]), np.radians([dec]), np.array([theta]), (1, 2), samples(15, 663))
    cells = HEALPIX.lonlat_to_healpix(lon.ravel(), lat.ravel())
    tile_count = np.zeros(len(cells), dtype=int)
    optical = np.zeros(len(cells), dtype=bool)
    common = np.zeros_like(optical)
    for tile, files in paths.items():
        weights = {b: mask_at(files[b], int(tile), b, cells) for b in COLOUR_BANDS}
        tile_count += np.logical_and.reduce([np.isfinite(v) for v in weights.values()])
        usable = np.logical_and.reduce([weights[b] >= PRIMARY[0] for b in ("VIS", "DECAM_r", "DECAM_i")])
        optical |= usable
        common |= usable & (weights["NIR_J"] >= PRIMARY[0])
    return {"represented_fraction": float((tile_count > 0).mean()),
            "overlap_fraction": float((tile_count > 1).mean()),
            "optical_fraction": float(optical.mean()), "common_fraction": float(common.mean())}


def core_offsets(core, paths):
    """Infer one tangent-plane translation per slit mask from bright core sources."""
    ra, dec = [], []
    for files in paths.values():
        with fits.open(files["MER"], memmap=True) as hdus:
            data = hdus[1].data
            i, _ = flux(data, "I_EXT_DECAM")
            bright = (data["VIS_DET"] == 1) & (i >= 10**((23.9 - 23.5) / 2.5))
            ra.extend(data["RIGHT_ASCENSION"][bright])
            dec.extend(data["DECLINATION"][bright])
    reference = SkyCoord(ra, dec, unit=u.deg)
    groups = defaultdict(list)
    for row in core:
        groups[row["File"].split("/")[0]].append(row)
    fits_by_mask = {}
    for name, rows in groups.items():
        sky = coordinates(rows)
        anchor, nearby, _, _ = reference.search_around_sky(sky, 9 * u.arcsec)
        east, north = sky[anchor].spherical_offsets_to(reference[nearby])
        delta = np.column_stack((east.arcsec, north.arcsec))
        best = None
        for guess in delta:
            residual = np.linalg.norm(delta - guess, axis=1)
            close = np.argsort(residual)
            close = close[residual[close] <= .65]
            _, first = np.unique(anchor[close], return_index=True)
            valid = close[first]
            score = (len(valid), -float(residual[valid].sum()))
            if best is None or score > best[0]:
                best = (score, valid)
        if best is None or len(best[1]) < max(5, int(np.ceil(.5 * len(rows)))):
            raise ValueError(f"No well-supported astrometric shift for {name}")
        offsets = delta[best[1]]
        shift = np.median(offsets, axis=0)
        held_out = np.array([
            np.linalg.norm(known - np.median(np.delete(offsets, i, axis=0), axis=0))
            for i, known in enumerate(offsets)
        ])
        fits_by_mask[name] = {
            "east_arcsec": float(shift[0]), "north_arcsec": float(shift[1]),
            "supporting_core_matches": len(offsets), "core_spectra": len(rows),
            "leave_one_out_rms_arcsec": float(np.sqrt(np.mean(held_out**2))),
        }
    return fits_by_mask


def shifted_control(sky, paths):
    """Count chance positional matches after eight local offset trials."""
    controls = concatenate([sky.directional_offset_by(angle * u.deg, 15 * u.arcsec)
                             for angle in range(0, 360, 45)])
    counts = np.zeros(len(controls), dtype=int)
    for files in paths.values():
        with fits.open(files["MER"], memmap=True) as hdus:
            data = hdus[1].data
            reference = SkyCoord(data["RIGHT_ASCENSION"], data["DECLINATION"], unit=u.deg)
            query, _, _, _ = reference.search_around_sky(controls, MATCH_ARCSEC * u.arcsec)
            counts += np.bincount(query, minlength=len(controls))
    return np.count_nonzero(counts.reshape(8, len(sky)) == 1, axis=1).tolist()


def measure(field, catalogue, paths, *, record_weights=False):
    spectra = catalogue["outskirts"]
    offsets = core_offsets(catalogue["core"], paths)
    raw_sky = coordinates(spectra)
    shifts = [offsets[r["File"].split("/")[0]] for r in spectra]
    sky = raw_sky.spherical_offsets_by([r["east_arcsec"] for r in shifts] * u.arcsec,
                                       [r["north_arcsec"] for r in shifts] * u.arcsec)
    centre = SkyCoord(field["ra_deg"], field["dec_deg"], unit=u.deg)
    registered_radius = centre.separation(sky).arcmin / field["theta500_arcmin"]
    if not np.all((registered_radius >= 1) & (registered_radius < 2)):
        raise ValueError("An astrometric shift crosses the radial sample boundary")
    by = defaultdict(list)
    raw = defaultdict(list)
    for tile, files in paths.items():
        for index, match in tile_match(sky, int(tile), files, record_weights=record_weights):
            by[index].append(match)
        for index, match in tile_match(raw_sky, int(tile), files):
            raw[index].append(match)
    sources = []
    groups = defaultdict(list)
    for j, row in enumerate(spectra):
        matches = by[j]
        hit = matches[0] if len(matches) == 1 else None
        if hit:
            groups[hit["object_id"]].append(j)
        sources.append({
            "name": row["Gal"], "file": row["File"], "ra_deg": float(row["RAJ2000"]),
            "dec_deg": float(row["DEJ2000"]), "spectroscopic_z": float(row["z"]),
            "spectroscopic_z_error": float(row["e_z"]), "r_over_r500": row["r_over_r500"],
            "registered_r_over_r500": float(registered_radius[j]),
            "dv_kms": row["dv_kms"], "nearby_mer_sources": len(matches), "match": hit,
        })
    fitsample = []
    for indices in groups.values():
        values = [sources[j] for j in indices]
        velocities = [v["dv_kms"] for v in values]
        if max(velocities) - min(velocities) > 500:
            raise ValueError(f"Redshifts disagree for repeated observations in {field['act_name']}")
        representative = min(values, key=lambda v: v["spectroscopic_z_error"])
        fitsample.append(representative["match"])
        for row in values:
            row["used_in_counts"] = row is representative
    tally = {}
    for selection in ("optical", "common_footprint", "j_detection",
                      "optical_allow_extended_area", "common_allow_extended_area"):
        hit = [r for r in fitsample if r[selection]]
        n, k = len(hit), int(sum(r["red_colour"] for r in hit))
        tally[selection] = {"count": n, "red": k, "wilson95": wilson(k, n)}
    return dict(field, area=joint_area(field, paths), slit_mask_offsets=offsets,
                unique_matches_before_registration=sum(len(v) == 1 for v in raw.values()),
                spectra_with_unique_mer_match=sum(len(v) == 1 for v in by.values()),
                shifted_control_unique_matches=shifted_control(sky, paths),
                unique_mer_matches=len(fitsample), tallies=tally, matched_spectra=sources)


def run(data, out):
    inputs = json.loads((HERE / "inputs.json").read_text())
    targets = inputs["catalogues"] + inputs["pilot_checks"]
    jobs = {row["file"]: (row["url"], data / row["file"]) for row in targets}
    for tile, maps in inputs["tiles"].items():
        for name, url in maps.items():
            jobs[(tile, name)] = (url, data / tile / url.rsplit("/", 1)[-1])
    with ThreadPoolExecutor(8) as pool:
        fetched = dict(zip(jobs, pool.map(lambda item: download(*item), jobs.values()), strict=True))
    pilot_data = defaultdict(dict)
    for entry in inputs["pilot_checks"]:
        pilot_data[entry["cluster"]][entry["archive"]] = read_tables(fetched[entry["file"]][0])
    ru = read_tables(fetched["spt_ruel.tsv"][0])["J/ApJ/792/45/table3"]
    gm = read_tables(fetched["spt_gmos.tsv"][0])
    act = Table.read(fetched["act_dr6_v1.fits"][0])
    moc = MOC.from_fits(fetched["mer_wide_survey.fits"][0])
    prev = HERE.parent / "act-cluster-coverage" / "results" / "effective_pilot.json"
    original = [c for c in json.loads(prev.read_text())["clusters"] if c["family"] == "MosaicMasks"]
    pilot = check_pilot(original, act, pilot_data, ru, gm["J/ApJS/227/3/table3"])
    counts, shortlist, candidates = distance_match(act, gm, moc)
    results = []
    for entry in shortlist:
        if entry["act_name"] in inputs["fields"]:
            tiles = inputs["fields"][entry["act_name"]]
            paths = {tile: {name: fetched[(tile, name)][0] for name in inputs["tiles"][tile]} for tile in tiles}
            results.append(measure(entry, candidates[entry["act_name"]], paths))
    out.mkdir(parents=True, exist_ok=True)
    result = {"pilot": pilot, "gmos_screen": counts, "gmos_shortlist": shortlist, "measured_fields": results,
              "sha256": {"/".join(k) if isinstance(k, tuple) else k: v[1] for k, v in fetched.items()}}
    (out / "spectroscopy_results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / "data")
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args()
    run(args.data, args.out)
