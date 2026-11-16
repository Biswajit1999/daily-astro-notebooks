"""Audit ranked DR1-F targets with observed FITS and independent archives."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy import units as u
from astropy.wcs import WCS
from matplotlib.patches import Circle
import matplotlib.pyplot as plt
import numpy as np
import requests
from scipy.ndimage import map_coordinates

from hats_extract import BUCKET, fetch_range
from screen import now

LEGACY = "https://www.legacysurvey.org/viewer/fits-cutout"
ESO = "https://archive.eso.org/tap_cat/sync"
BANDS = ("VIS", "Y", "J", "H", "DECam z")
SCALE = 0.13
WIDTH = 24
NPIX = round(WIDTH / SCALE) | 1


def download(url, params=None):
    response = requests.get(url, params=params, timeout=(12, 35))
    response.raise_for_status()
    return response.content, response.url


def s3_list(prefix):
    data, _ = download(BUCKET + "/", {"list-type": 2, "prefix": prefix})
    xml = ET.fromstring(data)
    if xml.findtext("{*}IsTruncated") == "true":
        raise ValueError(f"Truncated S3 object list for {prefix}")
    return [entry.text for entry in xml.findall("{*}Contents/{*}Key")]


def grid(ra, dec):
    result = WCS(naxis=2)
    result.wcs.crval = [ra, dec]
    result.wcs.crpix = [(NPIX+1)/2] * 2
    result.wcs.cdelt = [-SCALE/3600, SCALE/3600]
    result.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    result.wcs.radesys = "ICRS"
    return result


def fits_header(key):
    url = f"{BUCKET}/{key}"
    first, _, etag = fetch_range(url, (0, 28799))
    end_cards = next(i for i in range(0, len(first), 80) if first[i:i+8] == b"END     ")
    header_size = ((end_cards + 80 + 2879) // 2880) * 2880
    header = fits.Header.fromstring(first[:header_size].decode("ascii"), sep="")
    return header, header_size, first, etag


def euclid_crop(key, target_grid, header_data):
    url = f"{BUCKET}/{key}"
    header, header_size, first, etag = header_data
    nx, ny = header["NAXIS1"], header["NAXIS2"]
    if header["BITPIX"] != -32 or header["NAXIS"] != 2:
        raise ValueError("Unsupported Euclid mosaic FITS encoding")
    wcs = WCS(header).celestial
    y, x = np.indices((NPIX, NPIX))
    xx, yy = wcs.world_to_pixel_values(*target_grid.pixel_to_world_values(x, y))
    x0, x1 = max(0, int(np.floor(xx.min()))-2), min(nx, int(np.ceil(xx.max()))+3)
    y0, y1 = max(0, int(np.floor(yy.min()))-2), min(ny, int(np.ceil(yy.max()))+3)
    if x0 >= x1 or y0 >= y1:
        raise ValueError("FITS WCS excludes candidate cutout")
    start = header_size + 4*nx*y0
    end = header_size + 4*nx*y1 - 1
    raw, _, _ = fetch_range(url, (start, end), etag)
    image = np.frombuffer(raw, dtype=">f4").reshape(y1-y0, nx)[:, x0:x1].astype(float)
    image = image * header.get("BSCALE", 1.) + header.get("BZERO", 0.)
    repro = map_coordinates(image, [yy-y0, xx-x0], order=1, cval=np.nan)
    return repro, {"url": url, "etag": etag, "fits_header_sha256": hashlib.sha256(first[:header_size]).hexdigest(),
                   "data_range": [start, end], "data_range_sha256": hashlib.sha256(raw).hexdigest(),
                   "tile_id": header.get("TILEID", header.get("TILE_ID")), "bunit": header.get("BUNIT"),
                   "fwhm": header.get("FWHM"), "magzero": header.get("MAGZERO"), "pplanid": header.get("PPLANID")}


def legacy_crop(ra, dec, target_grid, output):
    params = {"ra": ra, "dec": dec, "layer": "ls-dr10", "pixscale": .262, "bands": "z", "size": 100}
    native = output / "DECam_z_native.fits"
    if native.exists():
        raw = native.read_bytes()
        url = requests.Request("GET", LEGACY, params=params).prepare().url
    else:
        raw, url = download(LEGACY, params)
        native.write_bytes(raw)
    with fits.open(io.BytesIO(raw)) as hdus:
        hdu = hdus[0]
        header = hdu.header
        y, x = np.indices((NPIX, NPIX))
        xx, yy = WCS(header).celestial.world_to_pixel_values(*target_grid.pixel_to_world_values(x, y))
        image = map_coordinates(np.squeeze(hdu.data), [yy, xx], order=1, cval=np.nan)
    return image, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(),
                   "bunit": header.get("BUNIT"), "release": header.get("VERSION"),
                   "brick": header.get("BRICK", header.get("BRICKNAM"))}


def local_image_metrics(image):
    axis = (np.arange(NPIX) - NPIX//2)*SCALE
    x, y = np.meshgrid(axis, axis)
    radius = np.hypot(x, y)
    background = image[(radius > 2) & (radius < 10)]
    finite = np.isfinite(background)
    if not finite.any():
        raise ValueError("No finite image background at the target")
    med = np.median(background[finite])
    rms = 1.4826 * np.median(np.abs(background[finite]-med))
    radius_aper = 0.8
    target = image[radius <= radius_aper]
    blank = []
    for bx in np.arange(-8, 9, 2):
        for by in np.arange(-8, 9, 2):
            if np.hypot(bx, by) <= 2.4:
                continue
            samples = image[np.hypot(x-bx, y-by) <= radius_aper]
            if np.isfinite(samples).all():
                blank.append(np.sum(samples-med)/len(samples))
    noise = 1.4826 * np.median(np.abs(blank-np.median(blank))) if len(blank) >= 20 else np.nan
    contrast = (np.mean(target-med)-np.median(blank))/noise if noise > 0 and np.isfinite(target).all() else None
    return {"finite_fraction": float(np.isfinite(image).mean()), "local_background": float(med),
            "pixel_mad_sigma": float(rms), "aperture_robust_snr": float(contrast) if contrast is not None else None,
            "blank_apertures": len(blank), "aperture_diameter_arcsec": 2*radius_aper}


def target_images(target, output):
    ra, dec = target["ra"], target["dec"]
    wcs = grid(ra, dec)
    tile = target["tileid"]
    images, manifest = {}, {}
    def one_band(band):
        try:
            directory = "VIS" if band == "VIS" else "NISP"
            token = "VIS" if band == "VIS" else f"NIR-{band}"
            keys = s3_list(f"dr1/MER/{tile}/{directory}/")
            deep = []
            for key in keys:
                if f"_BGSUB-MOSAIC-{token}_" in key and key.endswith(".fits"):
                    header_data = fits_header(key)
                    if "-DATA_RELEASE_DEEP-" in header_data[0].get("PPLANID", ""):
                        deep.append((key, header_data))
            if len(deep) != 1:
                raise ValueError(f"Expected one deep mosaic for {tile}/{band}, got {len(deep)}")
            key, header_data = deep[0]
            data, record = euclid_crop(key, wcs, header_data)
            return band, data, record
        except Exception as exc:
            return band, None, {"error": f"{type(exc).__name__}: {exc}"}

    with ThreadPoolExecutor(max_workers=4) as workers:
        for band, data, record in workers.map(one_band, BANDS[:-1]):
            manifest[band] = record
            if data is not None:
                images[band] = data
    try:
        images[BANDS[-1]], manifest[BANDS[-1]] = legacy_crop(ra, dec, wcs, output)
    except (requests.RequestException, ValueError, OSError) as exc:
        manifest[BANDS[-1]] = {"error": str(exc)}
    hdus = [fits.PrimaryHDU()]
    for band, data in images.items():
        try:
            manifest[band].update(local_image_metrics(data))
            hdus.append(fits.ImageHDU(data.astype(np.float32), wcs.to_header(), name=band.replace(" ", "_")))
        except ValueError as exc:
            manifest[band]["error"] = str(exc)
    if len(hdus) > 1:
        with gzip.open(output / "registered.fits.gz", "wb") as file:
            fits.HDUList(hdus).writeto(file)
        plot_cutouts(target, images, manifest, output / "cutouts.png")
    return manifest


def plot_cutouts(target, images, manifest, path):
    fig, axes = plt.subplots(1, 5, figsize=(11, 3.05), layout="constrained")
    extent = np.asarray([-1, 1, -1, 1]) * NPIX * SCALE / 2
    for ax, band in zip(axes, BANDS, strict=True):
        record = manifest.get(band, {})
        if "pixel_mad_sigma" in record:
            med, std = record["local_background"], record["pixel_mad_sigma"]
            if std <= 0:
                std = 1e-9
            scaled = np.arcsinh((images[band]-med)/std)
            ax.imshow(scaled, origin="lower", extent=extent, cmap="gray", vmin=-1, vmax=3.5)
            ax.add_patch(Circle((0, 0), 1.15, fill=False, lw=0.85, color="#ffc867"))
        else:
            ax.text(.5, .5, "Unavailable", ha="center", va="center", transform=ax.transAxes)
            ax.set(xlim=extent[:2], ylim=extent[2:])
        ax.set(title=f"Euclid {band}" if band != "DECam z" else "Blanco / DECam z",
               xticks=[], yticks=[])
    axes[0].plot([-9, -4], [-9, -9], color="white", lw=1.8)
    axes[0].text(-6.5, -8, '5″', color="white", ha="center", fontsize=8)
    axes[0].text(-9, 9, "N ↑   E ←", color="white", fontsize=8)
    fig.suptitle(f"{target['id']}  |  {target['ra']:.6f}°, {target['dec']:.6f}° (ICRS)", fontsize=12)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    options = parser.parse_args()
    results = options.results
    targets = json.loads((results / "summary.json").read_text())["audited"]
    out = results / "audit"
    out.mkdir(exist_ok=True)

    def one(target):
        output = out / target["id"]
        output.mkdir(exist_ok=True)
        image_data = target_images(target, output)
        return {**target, "images": image_data}

    with ThreadPoolExecutor(max_workers=3) as pool:
        audit = list(pool.map(one, targets))
    (results / "archive_audit.json").write_text(json.dumps({"utc": now(), "targets": audit}, indent=2) + "\n")


if __name__ == "__main__":
    main()
