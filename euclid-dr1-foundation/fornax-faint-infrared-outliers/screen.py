"""Run the preregistered DR1-Foundation Fornax colour screen."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import ascii

IRSA = "https://irsa.ipac.caltech.edu/TAP/sync"
CENTER = (52.933, -28.0885)
RADIUS = 0.125
MER = "euclid_dr1_mer_catalogue_deep_survey"
BANDS = ("y", "j", "h")
METHODS = ("templfit", "2fwhm_aper")
QUALITY = ("det_quality_flag", "flag_y", "flag_j", "flag_h")
BASE = ("object_id", "cntr", "tileid", "segmentation_map_id", "ra", "dec", "parent_id",
        "vis_det", "flag_vis", "ellipticity", "kron_radius", "fwhm",
        "flux_vis_2fwhm_aper", "fluxerr_vis_2fwhm_aper", *QUALITY)
COLUMNS = BASE + tuple(f"flux{error}_{band}_{method}"
                       for method in METHODS for band in BANDS for error in ("", "err"))
MAXREC = 100000


def flux(magnitude):
    return 10 ** ((23.9 - magnitude) / 2.5)


def cone(ra, dec, radius):
    return f"1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{radius}))"


def now():
    return datetime.now(timezone.utc).isoformat()


def tap(query, endpoint=IRSA, maxrec=MAXREC, timeout=75):
    response = requests.get(endpoint, params={
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
        "MAXREC": maxrec, "QUERY": query,
    }, timeout=timeout)
    response.raise_for_status()
    if response.content.lstrip().startswith(b"<"):
        raise ValueError(response.text[:1200])
    return response.content, response.url


def values(table, name):
    return np.ma.asarray(table[name], dtype=float).filled(np.nan)


def photometry(table, method):
    f = np.column_stack([values(table, f"flux_{b}_{method}") for b in BANDS])
    error = np.column_stack([values(table, f"fluxerr_{b}_{method}") for b in BANDS])
    with np.errstate(divide="ignore", invalid="ignore"):
        good = np.all(np.isfinite(f) & np.isfinite(error) & (f > 0) & (error > 0), axis=1)
        snr = np.where(good[:, None], f / error, np.nan)
        mags = 23.9 - 2.5 * np.log10(f)
        colour = mags[:, :2] - mags[:, 1:]
        sigma = np.hypot((2.5 / np.log(10)) / snr, 0.03)
        colour_error = sigma[:, :2] + sigma[:, 1:]
        yj, jh = colour.T
        e_yj, e_jh = colour_error.T
        margin = np.minimum.reduce([(yj - 0.1) / e_yj, (0.9 - yj) / e_yj, (-0.1 - jh) / e_jh])
    return colour, colour_error, snr, margin


def deduplicate(table, valid, good_flags, j_snr):
    coords = SkyCoord(values(table, "ra")[valid] * u.deg, values(table, "dec")[valid] * u.deg)
    valid_rows = np.flatnonzero(valid)
    a, b, _, _ = coords.search_around_sky(coords, 0.3 * u.arcsec)
    parent = list(range(len(table)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in zip(valid_rows[a[a < b]], valid_rows[b[a < b]], strict=True):
        parent[root(i)] = root(j)
    object_rows = {}
    for i in valid_rows:
        oid = int(table["object_id"][i])
        if oid in object_rows:
            parent[root(i)] = root(object_rows[oid])
        object_rows[oid] = i
    order = sorted(valid_rows, key=lambda i: (not good_flags[i],
                   -j_snr[i] if np.isfinite(j_snr[i]) else np.inf, int(table["cntr"][i])))
    representatives = {}
    for i in order:
        representatives.setdefault(root(i), i)
    primary = np.zeros(len(table), dtype=bool)
    primary[list(representatives.values())] = True
    return primary


def wilson(k, n):
    if n == 0:
        return None
    z = 1.95996398454
    p = k / n
    d = 1 + z*z/n
    m = p + z*z/(2*n)
    e = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return [max(0., (m-e)/d), min(1., (m+e)/d)]


def plot(out, tcol, acol, clean, selected, secure, audited):
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 4.0), sharex=True, sharey=True, layout="constrained")
    fig.patch.set_facecolor("white")
    for ax, col, title in zip(axes, (tcol, acol), ("MER template-fit", "PSF-matched aperture"), strict=True):
        xy = col[clean & ~selected]
        ax.scatter(*xy.T, s=5, color="#7893a6", alpha=.28, linewidths=0, label="J-selected controls")
        ax.scatter(*col[selected].T, s=26, color="#c7542d", edgecolor="white", linewidth=.3,
                   label="Template-box candidates")
        ax.scatter(*col[secure].T, s=65, facecolors="none", edgecolors="#007271", linewidth=1.2,
                   label="Secure in aperture")
        ax.plot([.1, .1, .9, .9], [-1.4, -.1, -.1, -1.4], "--", color="#26353f", lw=1)
        for rank, idx in enumerate(audited, 1):
            if np.all(np.isfinite(col[idx])):
                ax.annotate(f"F{rank:02}", col[idx], xytext=(5, 4 if rank % 2 else -10),
                            textcoords="offset points", fontsize=8)
        ax.set(xlabel="Y − J (AB mag)", title=title, xlim=(-.65, 1.35), ylim=(-1.05, .65))
        ax.grid(alpha=.16)
    axes[0].set_ylabel("J − H (AB mag)")
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles[:3 if secure.any() else 2], labels[:3 if secure.any() else 2],
                   loc="lower left", fontsize=7)
    fig.savefig(out / "colour_screen.png", dpi=165)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--cached", type=Path, help="Use an archived TAP CSV or CSV.GZ")
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    where = (f"{cone(*CENTER, RADIUS)} AND flux_j_templfit >= {flux(24):.14g} "
             f"AND flux_j_templfit < {flux(23):.14g}")
    query = f"SELECT {','.join(COLUMNS)} FROM {MER} WHERE {where} ORDER BY cntr"
    (out / "mer_query.adql").write_text(query + "\n")
    start = now()
    if args.cached:
        raw = gzip.decompress(args.cached.read_bytes()) if args.cached.suffix == ".gz" else args.cached.read_bytes()
        url = None
    else:
        raw, url = tap(query)
        check, _ = tap(f"SELECT COUNT(*) AS n FROM {MER} WHERE {where}")
    table = ascii.read(io.StringIO(raw.decode()).readlines(), format="csv", guess=False)
    if set(COLUMNS) - set(table.colnames) or len(table) >= MAXREC:
        raise ValueError("Unexpected MER columns or TAP row cap reached")
    if not args.cached:
        expected = int(ascii.read(check.decode().splitlines(), format="csv", guess=False)["n"][0])
        if expected != len(table):
            raise ValueError(f"Incomplete TAP extract: received {len(table)}, COUNT returned {expected}")
        (out / "mer_raw.csv.gz").write_bytes(gzip.compress(raw, mtime=0))

    valid = np.ones(len(table), dtype=bool)
    for col in ("object_id", "cntr", "ra", "dec", "flux_j_templfit"):
        valid &= np.isfinite(values(table, col))
    flags = (values(table, "parent_id") == -1)
    for col in QUALITY:
        flags &= values(table, col) == 0
    tc, te, ts, tm = photometry(table, METHODS[0])
    ac, ae, ans, am = photometry(table, METHODS[1])
    with np.errstate(divide="ignore", invalid="ignore"):
        j_snr = values(table, "flux_j_templfit") / values(table, "fluxerr_j_templfit")
    primary = deduplicate(table, valid, flags, j_snr)
    clean = primary & flags & np.all(ts >= 10, axis=1)
    selected = clean & (tm > 0)
    # Nominal counts use measurable aperture colours, with the separate S/N >= 5 rule for secure survivors.
    aperture = selected & (am > 0)
    secure = aperture & (am >= 2) & np.all(ans >= 5, axis=1)
    score = am if aperture.any() else tm
    rank_set = np.flatnonzero(aperture if aperture.any() else selected)
    audited = rank_set[np.lexsort((np.asarray(table["cntr"])[rank_set], -score[rank_set]))][:3]
    ids = np.full(len(table), "", dtype="U3")
    ids[audited] = [f"F{rank:02}" for rank in range(1, len(audited)+1)]
    for key, val in (("valid", valid), ("primary", primary), ("clean_flags", flags),
                     ("clean", clean), ("template_box", selected), ("aperture_box", aperture),
                     ("secure", secure), ("audit_id", ids)):
        table[key] = val
    for label, colour, error, snr, margin in (("template", tc, te, ts, tm), ("aperture", ac, ae, ans, am)):
        table[f"{label}_y_j"], table[f"{label}_j_h"] = colour.T
        table[f"{label}_y_j_err_bound"], table[f"{label}_j_h_err_bound"] = error.T
        table[f"{label}_min_snr"] = np.min(snr, axis=1)
        table[f"{label}_min_margin_sigma"] = margin
    table[selected].write(out / "screen_candidates.csv", format="ascii.csv", overwrite=True)
    with io.StringIO() as buffer:
        table.write(buffer, format="ascii.csv")
        (out / "full_quality_table.csv.gz").write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))
    summary = {"started_utc": start, "endpoint_url": url, "raw_sha256": hashlib.sha256(raw).hexdigest(),
               "raw_rows": len(table), "malformed": int((~valid).sum()),
               "duplicate_rows": int((valid & ~primary).sum()), "primary_rows": int(primary.sum()),
               "primary_clean_flags": int((primary & flags).sum()),
               "clean_controls": int((clean & ~selected).sum()), "clean": int(clean.sum()),
               "template_box": int(selected.sum()), "positive_aperture_photometry": int((selected & np.isfinite(am)).sum()),
               "nominal_aperture_box": int(aperture.sum()), "secure": int(secure.sum()),
               "nominal_wilson95": wilson(int(aperture.sum()), int(selected.sum())),
               "audited": [{"id": str(ids[i]), "object_id": int(table["object_id"][i]),
                            "tileid": int(table["tileid"][i]), "ra": float(table["ra"][i]),
                            "dec": float(table["dec"][i])} for i in audited]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    plot(out, tc, ac, clean, selected, secure, audited)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
