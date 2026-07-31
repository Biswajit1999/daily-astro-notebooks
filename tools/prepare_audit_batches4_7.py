"""Prepare compact, traceable inputs for Scientific Audit Batches 4--7.

Most inputs are exact archive tables already preserved by dense notebooks in
this repository.  The early notebooks that retained only a plot are converted
to clearly labelled *digitized display samples*.  These samples audit the old
output; they are never represented as replacements for the missing catalogue
rows.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/audit_batches4_7"


def coloured_pixels(path: Path, selector, bbox, xlim, ylim, stride=3):
    rgb = np.asarray(Image.open(path).convert("RGB"))
    mask = selector(rgb)
    y, x = np.where(mask)
    x0, y0, x1, y1 = bbox
    keep = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    x, y = x[keep][::stride], y[keep][::stride]
    xv = xlim[0] + (x - x0) / (x1 - x0) * (xlim[1] - xlim[0])
    yv = ylim[0] + (y - y0) / (y1 - y0) * (ylim[1] - ylim[0])
    return pd.DataFrame({"x": xv, "y": yv, "pixel_x": x, "pixel_y": y})


def prepare_exact_tables():
    DEST.mkdir(parents=True, exist_ok=True)
    copies = {
        ROOT / "gaia/2026-07-31-gaia-pleiades-membership-distance/gaia_query.csv": DEST / "pleiades_gaia_dr3_query.csv",
        ROOT / "exoplanet-archive/2026-07-31-exoplanet-radius-valley/confirmed_transiting_planets.csv": DEST / "exoplanet_transiting_archive.csv",
        ROOT / "exoplanet-archive/2026-07-31-hot-jupiter-tidal-circularisation/giant_planet_archive_query.csv": DEST / "exoplanet_composite_archive.csv",
        ROOT / "sdss/2026-07-31-sdss-bpt-galaxy-classification/sdss_bpt_query.csv": DEST / "sdss_emission_galaxies.csv",
    }
    for source, target in copies.items():
        shutil.copy2(source, target)

    upstream = Path("/tmp/ngc188/NGC_188_Filtered_Members_without_ruwe.csv")
    if not upstream.exists():
        raise FileNotFoundError("Clone https://github.com/chihuanbin/ngc188 to /tmp/ngc188 first")
    ngc = pd.read_csv(upstream)
    cols = ["source_id", "ra", "dec", "parallax", "parallax_error", "pmra", "pmra_error",
            "pmdec", "pmdec_error", "phot_g_mean_mag", "bp_rp", "ruwe", "distance_pc", "upmask_prob"]
    ngc[cols].to_csv(DEST / "ngc188_gaia_dr3_members.csv", index=False)


def prepare_digitized_outputs():
    orange = lambda a: (a[..., 0] > 240) & (a[..., 1] > 90) & (a[..., 1] < 225) & (a[..., 2] < 170)
    hy = coloured_pixels(ROOT / "gaia/2026-07-30-hr-diagram-hyades/hr_hyades.png", orange,
                         (74, 42, 822, 770), (-0.56, 4.43), (-0.75, 17.05), stride=2)
    hy.rename(columns={"x": "bp_rp_approx", "y": "absolute_g_approx"}).to_csv(DEST / "hyades_cmd_digitized_pixels.csv", index=False)

    red = lambda a: (a[..., 0] > 170) & (a[..., 1] < 90) & (a[..., 2] < 130)
    m67 = coloured_pixels(ROOT / "gaia/2026-07-30-proper-motion-membership-m67/m67_pm_members.png", red,
                          (88, 42, 691, 650), (-20, 20), (20, -20), stride=2)
    m67.rename(columns={"x": "pmra_approx", "y": "pmdec_approx"}).to_csv(DEST / "m67_member_plot_digitized_pixels.csv", index=False)

    teal = lambda a: (a[..., 1] > 90) & (a[..., 1] < 210) & (np.abs(a[..., 1].astype(int)-a[..., 2].astype(int)) < 12) & (a[..., 0] < 190)
    met = coloured_pixels(ROOT / "sdss/2026-07-30-metallicity-vs-position/feh_vs_lat.png", teal,
                          (94, 42, 822, 531), (35.8, 54.2), (0.35, -3.15), stride=3)
    met.rename(columns={"x": "galactic_latitude_approx_deg", "y": "feh_approx"}).to_csv(DEST / "sdss_metallicity_plot_digitized_pixels.csv", index=False)

    qred = lambda a: (a[..., 0] > 190) & (a[..., 1] < 180) & (a[..., 2] < 195)
    qblue = lambda a: (a[..., 2] > 130) & (a[..., 0] < 190) & (a[..., 1] > 80) & (a[..., 1] < 220)
    qso = coloured_pixels(ROOT / "sdss/2026-07-30-qso-vs-galaxy-colors/color_color.png", qred,
                          (78, 42, 822, 678), (-2.47, 3.60), (2.25, -3.73), stride=3)
    gal = coloured_pixels(ROOT / "sdss/2026-07-30-qso-vs-galaxy-colors/color_color.png", qblue,
                          (78, 42, 822, 678), (-2.47, 3.60), (2.25, -3.73), stride=3)
    qso["class"]="QSO"; gal["class"]="GALAXY"
    pd.concat([qso,gal],ignore_index=True).rename(columns={"x":"u_g_approx","y":"g_r_approx"}).to_csv(DEST / "sdss_colour_plot_digitized_pixels.csv",index=False)

    img=np.asarray(Image.open(ROOT/"sdss/2026-07-30-white-dwarf-spectrum/wd_spectrum.png").convert("RGB"))
    purple=(img[...,0]>55)&(img[...,0]<100)&(img[...,1]<25)&(img[...,2]>100)&(img[...,2]<170)
    rows=[]
    for x in range(120,1018):
        ys=np.where(purple[:,x])[0]
        ys=ys[(ys>=42)&(ys<=410)]
        if len(ys):
            wave=4000+(x-155)/0.1654; flux=(360-np.median(ys))/9.7
            rows.append((wave,flux,x,float(np.median(ys))))
    pd.DataFrame(rows,columns=["wavelength_approx_A","flux_approx","pixel_x","pixel_y"]).to_csv(DEST/"sdss_white_dwarf_plot_digitized.csv",index=False)


def main():
    prepare_exact_tables(); prepare_digitized_outputs()
    manifest = {
        "exact_tables": {
            "pleiades_gaia_dr3_query.csv": "Gaia DR3 query preserved by the 2026-07-31 Pleiades audit",
            "ngc188_gaia_dr3_members.csv": "Gaia DR3 member subset from chihuanbin/ngc188; upstream UPMASK probabilities retained",
            "exoplanet_transiting_archive.csv": "NASA Exoplanet Archive pscomppars query preserved on 2026-07-31",
            "exoplanet_composite_archive.csv": "NASA Exoplanet Archive pscomppars query preserved on 2026-07-31",
            "sdss_emission_galaxies.csv": "SDSS DR18 SQL result preserved by the BPT audit",
        },
        "digitized_legacy_outputs": {
            "hyades_cmd_digitized_pixels.csv": "approximate coloured pixels from hr_hyades.png; not catalogue rows",
            "m67_member_plot_digitized_pixels.csv": "approximate coloured pixels from m67_pm_members.png; not catalogue rows",
            "sdss_metallicity_plot_digitized_pixels.csv": "approximate coloured pixels from feh_vs_lat.png; not catalogue rows",
            "sdss_colour_plot_digitized_pixels.csv": "approximate coloured pixels from color_color.png; not catalogue rows",
            "sdss_white_dwarf_plot_digitized.csv": "approximately digitized plotted spectrum; not calibrated flux samples",
        },
    }
    (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (DEST/"README.md").write_text("# Inputs for Scientific Audit Batches 4–7\n\nExact preserved archive tables and explicitly labelled digitized legacy outputs. Read `manifest.json` before reuse. Digitized files support audits of old plots only; they are not substitutes for archive rows.\n")
    print(f"Prepared {len(list(DEST.iterdir()))} shared inputs")


if __name__ == "__main__":
    main()
