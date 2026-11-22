"""Measure component dominance in calibrated, registered cutouts."""
from argparse import ArgumentParser
import json
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree

from astropy.coordinates import SkyCoord
import numpy as np
from scipy.ndimage import gaussian_filter

from archive import BUCKET, get, image_hdu
from holdout_colours import BANDS, PIXEL

RADII = (.20, .28, .35)
EUCLID_PSF_BANDS = {"VIS": ("VIS", "VIS"), "J": ("NISP", "NIR-J"), "H": ("NISP", "NIR-H")}


def psf_metadata(tile):
    result = {}
    for band, (folder, token) in EUCLID_PSF_BANDS.items():
        query = urlencode({"list-type": 2, "prefix": f"dr1/MER/{tile}/{folder}/"})
        root = ElementTree.fromstring(get(f"{BUCKET}/?{query}"))
        keys = [elem.text for elem in root.findall(".//{*}Key")
                if f"CATALOG-PSF-{token}_" in elem.text]
        if len(keys) != 1:
            raise ValueError(f"Expected one catalogue PSF for {tile}, {band}")
        h, _, meta = image_hdu(f"{BUCKET}/{keys[0]}")
        result[band] = {**meta, "central_stamp_fwhm_arcsec": h["FWHM"]}
    return result


def psf_smoothed(image, native, target):
    if not 0 < native < target:
        raise ValueError("PSF smoothing requires a target FWHM above the native FWHM")
    sigma = np.sqrt(target**2-native**2)/(2.35482*PIXEL)
    return gaussian_filter(image, sigma)


def components(row):
    s = SkyCoord(row["ra"], row["dec"], unit="deg")
    p = SkyCoord([row["ra1"],row["ra2"]],[row["dec1"],row["dec2"]],unit="deg")
    dra, ddec = s.spherical_offsets_to(p)
    return np.column_stack((-dra.arcsec, ddec.arcsec))


def weighted_aperture(image, x, y, rad):
    yc, xc = (np.array(image.shape)-1)/2 + np.array([y, x])/PIXEL
    r = rad/PIXEL
    a, b = round(yc), round(xc)
    half = int(np.ceil(r+1))
    if min(a-half,b-half) < 0 or a+half >= image.shape[0] or b+half >= image.shape[1]:
        return np.nan
    patch = image[a-half:a+half+1, b-half:b+half+1]
    yy, xx = np.mgrid[a-half:a+half+1, b-half:b+half+1]
    subpixels = np.linspace(-.4,.4,5)
    cy, cx = np.meshgrid(subpixels, subpixels)
    coverage = np.mean((yy[...,None]+cy.ravel()-yc)**2+(xx[...,None]+cx.ravel()-xc)**2 <= r*r, axis=-1)
    inside = coverage>0
    return float(np.sum(patch[inside]*coverage[inside]))


def contrast(image, offsets):
    yy, xx = (np.indices(image.shape)-((np.array(image.shape)-1)/2)[:,None,None])*PIXEL
    sky_samples = image[(np.hypot(yy, xx) > 2.5) & (np.hypot(yy,xx) < 5.)]
    sky_samples = sky_samples[np.isfinite(sky_samples) & (sky_samples != 0)]
    if len(sky_samples)<50:
        return {}
    sky = np.median(sky_samples)
    sky_sigma = 1.4826*np.median(np.abs(sky_samples-sky))
    if sky_sigma<=0:
        return {}
    sky = np.median(sky_samples[np.abs(sky_samples-sky) < 3.*sky_sigma])
    a = image-sky
    metrics = {}
    for radius in RADII:
        f = np.array([weighted_aperture(a, *point, radius) for point in offsets])
        blanks = []
        for k, ring in enumerate((3.,4.4,5.6)):
            for az in (np.arange(12)+k/3)*2*np.pi/12:
                shift = ring*np.array([np.cos(az),np.sin(az)])
                sample = [weighted_aperture(a, *point, radius) for point in offsets+shift]
                if np.isfinite(sample).all():
                    blanks.append(sample)
        if len(blanks)<18 or not np.isfinite(f).all():
            continue
        pairs = np.array(blanks)
        diffs = pairs[:,0]-pairs[:,1]
        noise = float(1.4826*np.median(np.abs(diffs-np.median(diffs))))
        diff = float(f[0]-f[1])
        metrics[str(radius)] = {
            "flux_a_b_native_summed": f.tolist(), "a_minus_b_flux": diff, "background_difference_mad": noise,
            "a_minus_b_in_background_mad": diff/noise if noise>0 else None, "blank_pair_placements": len(blanks),
            "b_minus_a_aperture_mag": float(2.5*np.log10(f[0]/f[1])) if np.min(f)>0 else None,
        }
    return metrics


def evaluate(cache, selected):
    out = {}
    for row in selected["candidates"]:
        name = row["candidate"]
        offsets = components(row)
        path = cache/f"{name}.npz"
        if not path.exists():
            continue
        with np.load(path) as cube:
            bands = {band: contrast(cube[band], offsets) for band in BANDS if band in cube}
        attested = bool(all(str(r) in bands.get(band,{}) and
                            sign*(bands[band][str(r)]["a_minus_b_in_background_mad"] or 0.)>5
                            for band, sign in (("VIS",1),("J",-1),("H",-1)) for r in RADII))
        out[name] = {"tangent_xy_arcsec": offsets.tolist(), "three_band_rank_reversal": attested, "bands": bands}
    return out


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    p = args.cache
    selected = json.loads((p/"selection.json").read_text())
    report = evaluate(p, selected)
    target = selected["candidates"][0]
    psf = psf_metadata(target["tile"])
    name = target["candidate"]
    with np.load(p/f"{name}.npz") as cube:
        matched = {
            str(width): {band: contrast(psf_smoothed(cube[band], meta["central_stamp_fwhm_arcsec"], width),
                                      components(target)) for band, meta in psf.items()}
            for width in (.65,.8)
        }
    out = {"candidates": report, "lead_psf_metadata": psf, "lead_smoothed_apertures": matched}
    (p/"aperture_checks.json").write_text(json.dumps(out, indent=2, allow_nan=False)+"\n")
