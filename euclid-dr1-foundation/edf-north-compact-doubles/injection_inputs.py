"""Extract observed quiet-sky stamps and local stellar J profiles."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from astropy.io import ascii
from astropy.wcs import WCS
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares

from archive import image_strip
from search_doubles import dog, robust


TILES = (101829775, 101829777, 101829779, 101830399, 101830403, 101830407)
STAMPS = 6
HALF = 74
GRID = np.mgrid[-12:13, -12:13].astype(float)


def gaia_table(gaia_root, tile, wcs):
    ra, dec = wcs.wcs.crval
    params = dict(catalog="gaia_dr3_source", objstr=f"{ra:.7f} {dec:+.7f}",
                  spatial="cone", radius="420", radunits="arcsec", outfmt="1")
    url = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?" + urlencode(params)
    raw = gaia_root / f"{tile}.tbl"
    if not raw.exists():
        with urlopen(url, timeout=40) as response:
            data = response.read()
        raw.write_bytes(data)
    return ascii.read(raw, format="ipac"), url, hashlib.sha256(raw.read_bytes()).hexdigest()


def col(table, field):
    return np.ma.filled(np.ma.array(table[field], dtype=float), np.nan)


def model(values):
    amplitude, x0, y0, sx, sy, angle, baseline = values
    y, x = GRID
    dx, dy = x-x0, y-y0
    p = np.cos(angle)*dx + np.sin(angle)*dy
    q = -np.sin(angle)*dx + np.cos(angle)*dy
    return baseline + amplitude * np.exp(-.5*((p/sx)**2+(q/sy)**2))


def measured_profile(a, gx, gy):
    if min(gx, gy) < 13 or gx >= a.shape[1]-13 or gy >= a.shape[0]-13:
        return None
    x, y = int(round(gx)), int(round(gy))
    patch = np.array(a[y-12:y+13, x-12:x+13], dtype=float)
    radius = np.hypot(*GRID)
    if not np.isfinite(patch).all() or np.any(patch == 0):
        return None
    med, noise = robust(patch[(radius >= 8) & (radius <= 11)])
    peak = patch[10:15, 10:15].max() - med
    if noise <= 0 or not (45 < peak/noise < 2500):
        return None
    sample = radius <= 7.5
    result = least_squares(
        lambda p: (model(p)[sample]-patch[sample])/peak,
        [peak, gx-x, gy-y, 1.65, 1.65, 0, med],
        bounds=([.35*peak, -2, -2, .85, .85, -np.pi, med-.1*peak],
                [1.8*peak, 2, 2, 3, 3, np.pi, med+.1*peak]),
        loss="soft_l1", f_scale=.035,
    )
    amp, x0, y0, sx, sy, _, bg = result.x
    if (not result.success or np.hypot(gx-x-x0, gy-y-y0) > 1.2
            or min(sx, sy)/max(sx, sy) < .7 or np.std(result.fun) > .11
            or np.max(patch[(radius>=6) & (radius<=10)]-bg) > .13*amp):
        return None
    centred = map_coordinates(patch - bg, GRID + np.array([12+y0, 12+x0])[:, None, None],
                              order=3, mode="nearest")
    norm = centred[radius < 6].sum()
    if norm <= 0:
        return None
    return centred/norm, float(2.354820*.1*np.sqrt(sx*sy)), float(peak/noise)


def quiet_stamps(a, seed):
    rng = np.random.default_rng(seed)
    crops, positions = [], []
    core = np.hypot(*np.mgrid[-HALF:HALF+1, -HALF:HALF+1]) <= 10
    ann = np.hypot(*np.mgrid[-HALF:HALF+1, -HALF:HALF+1])
    ann = (ann >= 20) & (ann <= 65)
    for _ in range(1500):
        y = int(rng.integers(HALF+20, a.shape[0]-HALF-20))
        x = int(rng.integers(HALF+20, a.shape[1]-HALF-20))
        if any(np.hypot(y-yy, x-xx) < 2*HALF+2 for yy, xx in positions):
            continue
        patch = np.array(a[y-HALF:y+HALF+1, x-HALF:x+HALF+1], dtype=np.float32)
        filtered, good = dog(patch, 1.25, 3.5)
        if not good.all():
            continue
        med, noise = robust(filtered[ann])
        if noise <= 0 or np.max(np.abs(filtered[core]-med)) > 4.5*noise:
            continue
        positions.append((y, x))
        crops.append(patch)
        if len(crops) == STAMPS:
            return np.asarray(crops), positions
    raise ValueError("Insufficient quiet stamps")


def extract(tile, pilot_cache, holdout_cache, gaia_root, out):
    cache = pilot_cache if tile < 101829781 else holdout_cache
    a, header, meta = image_strip(tile, "J", cache)
    wcs = WCS(header).celestial
    table, url, sha = gaia_table(gaia_root, tile, wcs)
    g = col(table, "phot_g_mean_mag")
    use = ((g >= 17) & (g <= 21) & (col(table, "ruwe") < 1.35)
           & (col(table, "parallax_over_error") > 4) & (col(table, "ipd_frac_multi_peak") < 5)
           & (col(table, "pm") < 45))
    tab = table[use]
    # 2025 is the approximate observing epoch for this proper-motion correction.
    delta = 2025.0 - col(tab, "ref_epoch")
    dec = col(tab, "dec")
    ra = col(tab, "ra") + delta*col(tab, "pmra")/3.6e6/np.cos(np.deg2rad(dec))
    dec = dec + delta*col(tab, "pmdec")/3.6e6
    x, y = wcs.world_to_pixel_values(ra, dec)
    x -= meta["origin_xy"][0]
    y -= meta["origin_xy"][1]
    shapes, stars = [], []
    for entry, gx, gy in zip(tab, x, y, strict=True):
        profile = measured_profile(a, gx, gy)
        if profile is not None:
            stamp, fwhm, snr = profile
            shapes.append(stamp)
            stars.append({"gaia_dr3_id": str(entry["source_id"]), "fwhm_arcsec": fwhm,
                          "peak_over_local_mad": snr, "cutout_x": float(gx), "cutout_y": float(gy)})
    if len(shapes) < 3:
        raise ValueError(f"Only {len(shapes)} eligible stars in tile {tile}")
    profile = np.maximum(np.median(shapes, axis=0), 0)
    profile[np.hypot(*GRID) >= 10] = 0
    profile /= profile.sum()
    noise, positions = quiet_stamps(a, seed=tile+181126)
    np.savez_compressed(out/f"background_{tile}.npz", stamps=noise, profile=profile)
    return {"tile": tile, "archive": meta, "gaia_query": url, "gaia_sha256": sha,
            "stars": stars, "background_xy": [[x, y] for y, x in positions],
            "median_fwhm_arcsec": float(np.median([s["fwhm_arcsec"] for s in stars]))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-cache", type=Path, required=True)
    p.add_argument("--holdout-cache", type=Path, required=True)
    p.add_argument("--gaia", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.gaia.mkdir(parents=True, exist_ok=True)
    a.output.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as executor:
        jobs = [executor.submit(extract, tile, a.pilot_cache, a.holdout_cache,
                                a.gaia, a.output) for tile in TILES]
        result = [j.result() for j in jobs]
    (a.output/"injection_provenance.json").write_text(json.dumps(result, indent=2)+"\n")
    print([(p["tile"], len(p["stars"]), p["median_fwhm_arcsec"]) for p in result])


if __name__ == "__main__":
    main()
