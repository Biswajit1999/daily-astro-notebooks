"""Measure the Euclid DR1-Foundation cut on public DESI DR1 LRG data and random pairs."""
from argparse import ArgumentParser
from hashlib import file_digest
import json
from pathlib import Path

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import FlatLambdaCDM
from astropy.io import fits
from astropy_healpix import HEALPix
from mocpy import MOC
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
SKY = 4*np.pi*(180/np.pi)**2
DESI_BASE = "https://data.desi.lbl.gov/public/dr1/survey/catalogs/dr1/LSS/iron/LSScats/v1.5/"
EUCLID_BASE = "https://nasa-irsa-euclid-dr1.s3.us-east-1.amazonaws.com/dr1/MOC/"
SHELL = (95., 115.)
Z_BINS = ((.4, .6), (.6, .8), (.8, 1.1))
MU_EDGES = np.linspace(0., 1., 6)
COSMOLOGY = FlatLambdaCDM(H0=100., Om0=.315)
RANDOM_DIVISOR = 32
INSIDE_DIVISOR = 4
SEED = 20261120
MASK_FILES = {
    "mer_wide": "euclid_dr1_mer_catalogue_wide_survey.moc.fits",
    "wide_tiles": "euclid_dr1_wide.moc.moc.fits",
}
CONTROL_KEYS = ("cap_a", "cap_b", "cap_c")
CAPS = ("NGC", "SGC")
SOURCES = {name: EUCLID_BASE+name for name in MASK_FILES.values()}
for cap in CAPS:
    for kind in ("clustering.dat", "0_clustering.ran"):
        name = f"LRG_{cap}_{kind}.fits"
        SOURCES[name] = DESI_BASE+name


def mask_inventory(cache):
    masks = {key: MOC.from_fits(cache/name) for key, name in MASK_FILES.items()}
    hpx = HEALPix(nside=256, order="nested")
    counts = np.zeros(hpx.npix, dtype=np.int64)
    for cap in CAPS:
        with fits.open(cache/f"LRG_{cap}_0_clustering.ran.fits", memmap=True) as hdus:
            table = hdus[1].data
            for start in range(0, len(table), 500_000):
                rows = table[start:start+500_000]
                good = (rows["WEIGHT"] > 0) & (rows["WEIGHT_FKP"] > 0)
                pix = hpx.lonlat_to_healpix(rows["RA"][good]*u.deg, rows["DEC"][good]*u.deg)
                counts += np.bincount(pix, minlength=hpx.npix)
    area = {}
    for name, pix_counts, depth, threshold in (
        ("nside128_one", counts.reshape(-1, 4).sum(axis=1), 7, 1),
        ("nside256_one", counts, 8, 1),
        ("nside256_five", counts, 8, 5),
    ):
        pixels = np.flatnonzero(pix_counts >= threshold).astype(np.uint64)
        proxy = MOC.from_healpix_cells(pixels, np.full(len(pixels), depth, dtype=np.uint8), max_depth=depth)
        area[name] = {"desi_random_support_deg2": proxy.sky_fraction*SKY,
                      **{key: {"euclid_deg2": mask.sky_fraction*SKY,
                               "overlap_deg2": mask.intersection(proxy).sky_fraction*SKY}
                         for key, mask in masks.items()}}
    return masks, counts, area, proxy


def cap_controls(support, excluded, area_deg2):
    """Place disjoint, nearly fully sampled caps of the primary overlap's nominal area."""
    radius = np.arccos(1-2*area_deg2/SKY)*u.rad
    grid = HEALPix(nside=8, order="nested")
    lon, lat = grid.healpix_to_lonlat(np.arange(grid.npix))
    coords = SkyCoord(lon, lat)
    candidates = {}
    for index in np.flatnonzero(support.contains_lonlat(lon, lat)):
        cap = MOC.from_cone(lon[index], lat[index], radius=radius, max_depth=11)
        supported = cap.intersection(support).sky_fraction/cap.sky_fraction
        if supported >= .97 and cap.intersection(excluded).sky_fraction == 0:
            candidates[index] = (cap, supported)
    placed, controls, info = [], {}, {}
    for name in CONTROL_KEYS:
        if not candidates:
            raise ValueError("Insufficient compact controls in DESI footprint")
        distances = {i: (180. if not placed else coords[i].separation(coords[placed]).deg.min())
                     for i in candidates}
        index = max(candidates, key=lambda i: (distances[i], candidates[i][1], -i))
        if distances[index] < 2*radius.to_value(u.deg):
            raise ValueError("Compact control caps could not be placed without overlap")
        cap, fraction = candidates.pop(index)
        controls[name] = cap
        placed.append(index)
        info[name] = {"ra_deg": lon[index].deg, "dec_deg": lat[index].deg,
                      "radius_deg": radius.to_value(u.deg), "moc_area_deg2": cap.sky_fraction*SKY,
                      "desi_support_fraction": fraction}
    return controls, info


def read_columns(table, rows, include_ids=False):
    names = ["RA", "DEC", "Z", "WEIGHT", "WEIGHT_FKP"]
    if include_ids:
        names.append("TARGETID")
    return {name: np.array(table[name][rows], dtype=np.int64 if name == "TARGETID" else np.float64)
            for name in names}


def concatenate(*samples):
    return {key: np.concatenate([sample[key] for sample in samples]) for key in samples[0]}


def read_lrg(cache, masks):
    galaxies, random_sets = [], [[], []]
    rng = np.random.default_rng(SEED)
    thin_log = {}
    for cap in CAPS:
        with fits.open(cache/f"LRG_{cap}_clustering.dat.fits", memmap=True) as hdus:
            galaxies.append(read_columns(hdus[1].data, slice(None), include_ids=True))
        with fits.open(cache/f"LRG_{cap}_0_clustering.ran.fits", memmap=True) as hdus:
            table = hdus[1].data
            chunks = [[], []]
            zero_count = 0
            for start in range(0, len(table), 500_000):
                rows = table[start:start+500_000]
                pos = {"RA": rows["RA"], "DEC": rows["DEC"]}
                probabilities = np.where(in_masks(pos, masks).any(axis=1), 1/INSIDE_DIVISOR, 1/RANDOM_DIVISOR)
                positive = (rows["WEIGHT"] > 0) & (rows["WEIGHT_FKP"] > 0)
                zero_count += int((~positive).sum())
                draws = rng.random(len(rows))
                for cohort, dest in enumerate(chunks):
                    take = positive & (draws >= cohort*probabilities) & (draws < (cohort+1)*probabilities)
                    data = read_columns(rows, take)
                    data["SELECTION_PROBABILITY"] = probabilities[take]
                    dest.append(data)
            sizes = []
            for dest, chunk_list in zip(random_sets, chunks):
                sample = concatenate(*chunk_list)
                dest.append(sample)
                sizes.append(len(sample["Z"]))
            thin_log[cap] = {"available_rows": len(table), "excluded_nonpositive_weights": zero_count,
                             "rows_per_thinning": sizes}
    all_galaxies = concatenate(*galaxies)
    if len(np.unique(all_galaxies["TARGETID"])) != len(all_galaxies["TARGETID"]):
        raise ValueError("LRG clustering tables do not have unique TARGETIDs")
    return all_galaxies, [concatenate(*random) for random in random_sets], thin_log


def in_masks(sample, masks):
    return np.column_stack([mask.contains_lonlat(sample["RA"]*u.deg, sample["DEC"]*u.deg)
                            for mask in masks.values()])


def redshift_mask(sample, zlim):
    return (sample["Z"] >= zlim[0]) & (sample["Z"] < zlim[1])


def count_rows(sample, membership, mask_names, zlim):
    z = redshift_mask(sample, zlim)
    w = sample["WEIGHT"]*sample["WEIGHT_FKP"]/sample.get("SELECTION_PROBABILITY", 1.)
    return {"n": int(z.sum()), "weight": float(w[z].sum()),
            "inside": {key: {"n": int((z & membership[:, col]).sum()),
                             "weight": float(w[z & membership[:, col]].sum())}
                       for col, key in enumerate(mask_names)}}


def cartesian(sample, z):
    ra, dec = np.deg2rad(sample["RA"][z]), np.deg2rad(sample["DEC"][z])
    grid = np.linspace(Z_BINS[0][0], Z_BINS[-1][1], 4097)
    distance = np.interp(sample["Z"][z], grid, COSMOLOGY.comoving_distance(grid).value)
    return distance[:, None]*np.column_stack([np.cos(dec)*np.cos(ra), np.cos(dec)*np.sin(ra), np.sin(dec)])


def count_pairs(xyz, weight, inside):
    """Use unordered pairs and the midpoint line of sight; count included endpoints."""
    n_mu = len(MU_EDGES)-1
    full = np.zeros(n_mu)
    raw_count = np.zeros(n_mu, dtype=np.int64)
    both = np.zeros((inside.shape[1], n_mu))
    endpoints = np.zeros_like(both)
    tree = cKDTree(xyz)
    for start in range(0, len(xyz), 2048):
        block = cKDTree(xyz[start:start+2048])
        pairs = block.sparse_distance_matrix(tree, SHELL[1], output_type="ndarray")
        keep = (pairs["j"] > pairs["i"]+start) & (pairs["v"] >= SHELL[0]) & (pairs["v"] < SHELL[1])
        i, j, sep = pairs["i"][keep]+start, pairs["j"][keep], pairs["v"][keep]
        midpoint = xyz[i]+xyz[j]
        mu = np.abs(np.einsum("ij,ij->i", xyz[j]-xyz[i], midpoint))/(sep*np.linalg.norm(midpoint, axis=1))
        idx = np.minimum(n_mu-1, np.searchsorted(MU_EDGES, mu, side="right")-1)
        w = weight[i]*weight[j]
        full += np.bincount(idx, w, minlength=n_mu)
        raw_count += np.bincount(idx, minlength=n_mu)
        for col in range(inside.shape[1]):
            i_in, j_in = inside[i, col], inside[j, col]
            both[col] += np.bincount(idx, w*(i_in & j_in), minlength=n_mu)
            endpoints[col] += np.bincount(idx, w*(i_in.astype(int)+j_in), minlength=n_mu)
    return full, raw_count, both, endpoints


def pair_result(sample, membership, mask_names, zlim):
    z = redshift_mask(sample, zlim)
    w = sample["WEIGHT"][z]*sample["WEIGHT_FKP"][z]/sample["SELECTION_PROBABILITY"][z]
    if not np.all(np.isfinite(w) & (w > 0)):
        raise ValueError("Expected finite positive clustering weight in all selected rows")
    full, raw, both, end = count_pairs(cartesian(sample, z), w, membership[z])
    return {"full_pairs": raw.tolist(), "full_weighted_pairs": full.tolist(),
            "inside": {key: {"both_pair_weight": both[col].tolist(),
                             "one_or_two_endpoint_weight": end[col].tolist(),
                             "full_pair_fraction": (both[col]/full).tolist(),
                             "conditional_partner_fraction": (2*both[col]/end[col]).tolist()}
                       for col, key in enumerate(mask_names)}}


def input_hashes(cache):
    sources = {}
    for name, url in SOURCES.items():
        with (cache/name).open("rb") as source:
            sources[name] = {"url": url, "bytes": (cache/name).stat().st_size,
                             "sha256": file_digest(source, "sha256").hexdigest()}
    pinned = HERE/"input_files.json"
    if pinned.exists() and sources != json.loads(pinned.read_text()):
        raise ValueError("Input files differ from the recorded release files")
    return sources


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE/"results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = input_hashes(args.cache)
    masks, spatial_counts, area, support = mask_inventory(args.cache)
    caps, control_info = cap_controls(support, masks["mer_wide"].union(masks["wide_tiles"]),
                                      area["nside256_five"]["mer_wide"]["overlap_deg2"])
    masks.update(caps)
    galaxies, random_sets, thin_log = read_lrg(args.cache, masks)
    gals_in = in_masks(galaxies, masks)
    ran_in = [in_masks(random, masks) for random in random_sets]
    report = {"area": area, "separation_h_inverse_mpc": list(SHELL), "thinning_seed": SEED,
              "thinning": thin_log, "inside_inclusion_probability": 1/INSIDE_DIVISOR,
              "outside_inclusion_probability": 1/RANDOM_DIVISOR, "mu_edges": MU_EDGES.tolist(),
              "control_caps": control_info, "bins": []}
    for zlim in Z_BINS:
        row = {"z": list(zlim), "galaxies": count_rows(galaxies, gals_in, masks, zlim), "randoms": []}
        for sample, membership in zip(random_sets, ran_in):
            row["randoms"].append({"counts": count_rows(sample, membership, masks, zlim),
                                   "pairs": pair_result(sample, membership, masks, zlim)})
        report["bins"].append(row)
        print(f"{zlim}: {row['galaxies']['inside']}", flush=True)
    (args.output/"window_measurements.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    (args.output/"window_input_check.json").write_text(json.dumps(inputs, indent=2, sort_keys=True)+"\n")
    np.save(args.cache/"desi_random_nside256_nested_counts.npy", spatial_counts)


if __name__ == "__main__":
    main()
