"""Prepare compact, traceable SN 1987A products for Scientific Audit Batch 3.

The script expects the exact MAST products downloaded under
``/tmp/astro-batch3``. It strips unrelated FITS extensions and keeps a
10.8-arcsec cutout around the remnant, preserving science values, errors, WCS,
units, filter, observation date, and original product name.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
import astropy.units as u

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/tmp/astro-batch3")
DEST = ROOT / "data/sn1987a"
TARGET = SkyCoord("05h35m27.987s -69d16m11.11s")


def compact_fits(source: Path, destination: Path, size_arcsec: float = 10.8) -> dict:
    with fits.open(source, memmap=False) as hdul:
        primary = hdul[0].header
        science_hdu = hdul["SCI"]
        science = np.asarray(science_hdu.data, dtype=np.float32)
        wcs = WCS(science_hdu.header)
        cut = Cutout2D(science, TARGET, size_arcsec * u.arcsec, wcs=wcs, mode="partial", fill_value=np.nan)
        header = cut.wcs.to_header()
        header["BUNIT"] = science_hdu.header.get("BUNIT", "unknown")
        header["FILTER"] = primary.get("FILTER", "unknown")
        header["DATE-OBS"] = primary.get("DATE-OBS", "unknown")
        header["ORIGFILE"] = source.name
        output = [fits.PrimaryHDU(header=fits.Header({"ORIGIN": "MAST compact cutout", "ORIGFILE": source.name}))]
        output.append(fits.ImageHDU(cut.data.astype(np.float32), header=header, name="SCI"))
        if "ERR" in hdul:
            error = np.asarray(hdul["ERR"].data, dtype=np.float32)
            err_cut = Cutout2D(error, TARGET, size_arcsec * u.arcsec, wcs=wcs, mode="partial", fill_value=np.nan)
            output.append(fits.ImageHDU(err_cut.data.astype(np.float32), header=header, name="ERR"))
        fits.HDUList(output).writeto(destination, overwrite=True)
        return {
            "path": str(destination.relative_to(ROOT)),
            "source_product": source.name,
            "filter": primary.get("FILTER"),
            "date_obs": primary.get("DATE-OBS"),
            "unit": science_hdu.header.get("BUNIT"),
            "shape": list(cut.data.shape),
        }


def write_photometry() -> None:
    epochs = np.array([8717, 9480, 9974, 10317, 10698, 11119, 11458, 11837, 12218, 12598])
    records = []
    values = {
        "F438W": {
            "er": ([2.417,2.249,2.115,2.026,1.922,1.749,1.667,1.534,1.411,1.282], [.002,.002,.002,.002,.002,.001,.001,.001,.001,.001]),
            "ejecta": ([.958,1.015,1.041,1.056,1.096,1.093,1.065,1.078,1.099,1.076], [.003,.004,.004,.004,.005,.004,.004,.004,.004,.004]),
            "center": ([7.179,7.665,7.638,7.561,8.071,7.874,7.679,7.907,7.857,7.387], [.090,.101,.101,.101,.147,.095,.101,.103,.104,.099]),
        },
        "F625W": {
            "er": ([2.286,2.073,1.942,1.854,1.761,1.609,1.525,1.393,1.280,1.191], [.001,.001,.001,.001,.001,.001,.001,.001,.001,.001]),
            "ejecta": ([.650,.707,.726,.743,.770,.782,.770,.767,.785,.779], [.001,.001,.001,.001,.002,.001,.001,.001,.001,.002]),
            "center": ([5.372,5.836,5.910,5.968,6.198,6.102,5.967,5.890,6.098,5.737], [.038,.039,.039,.039,.056,.040,.039,.039,.040,.041]),
        },
    }
    unit_scales = {"er": "1e-15", "ejecta": "1e-16", "center": "1e-18"}
    for filt, regions in values.items():
        for region, (fluxes, errors) in regions.items():
            for epoch, flux, error in zip(epochs, fluxes, errors):
                records.append({"epoch_days_since_1987_02_23":epoch,"filter":filt,"region":region,"flux":flux,"flux_error":error,"flux_scale_erg_cm-2_s-1_A-1":unit_scales[region]})
    pd.DataFrame(records).to_csv(DEST / "hst_photometry_rosu2024_table6.csv", index=False)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    frames = DEST / "hst_release_frames"
    frames.mkdir(exist_ok=True)
    dates = {
        "1994": "1994-09-24", "1998": "1998-02-06", "2001": "2001-03-23",
        "2003": "2003-01-05", "2004": "2004-12-15", "2006": "2006-12-06",
    }
    for year in dates:
        shutil.copy2(SOURCE / f"nasa_frames/sn1987a_{year}.jpg", frames / f"sn1987a_{year}.jpg")
    pd.DataFrame([{"year":int(year),"date":date,"file":f"sn1987a_{year}.jpg"} for year,date in dates.items()]).to_csv(frames / "frames.csv", index=False)

    products = []
    for filt in ["f150w", "f200w", "f356w", "f444w"]:
        source = next(SOURCE.glob(f"mastDownload/JWST/*{filt}*/*_i2d.fits"))
        products.append(compact_fits(source, DEST / f"jwst_{filt}_2022_cutout.fits"))
    hst_source = next(SOURCE.glob("mastDownload/HST/*/*_drc.fits"))
    products.append(compact_fits(hst_source, DEST / "hst_f625w_2018_cutout.fits"))
    write_photometry()

    manifest = {
        "target": "SN 1987A",
        "coordinate_icrs": {"ra_deg": TARGET.ra.deg, "dec_deg": TARGET.dec.deg},
        "products": products,
        "release_frames": [
            {"date": date, "file": f"data/sn1987a/hst_release_frames/sn1987a_{year}.jpg", "source": "NASA Hubble release, February 2007 collection"}
            for year,date in dates.items()
        ],
        "photometry": {
            "path": "data/sn1987a/hst_photometry_rosu2024_table6.csv",
            "source": "Rosu et al. 2024, ApJ 966 238, Table 6",
            "doi": "10.3847/1538-4357/ad36cc",
        },
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (DEST / "README.md").write_text(
        "# SN 1987A shared data\n\nCompact calibrated MAST cutouts, official NASA Hubble release frames, and the peer-reviewed HST photometry used by Scientific Audit Batch 3. See `manifest.json` for exact provenance.\n"
    )
    print(f"Prepared {len(products)} compact FITS products in {DEST}")


if __name__ == "__main__":
    main()
