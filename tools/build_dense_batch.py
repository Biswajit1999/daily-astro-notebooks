"""Build the 2026-07-31 dense notebook batch.

The notebooks are generated from explicit cell lists so that their structure is
consistent, reviewable, and easy to extend. Run them with:

    python tools/run_notebooks.py --date 2026-07-31
"""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-07-31"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


COMMON_IMPORTS = """
from pathlib import Path
import json
import io
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

warnings.filterwarnings("ignore", category=RuntimeWarning)
plt.style.use("seaborn-v0_8-whitegrid")
COLORS = {"navy": "#071426", "blue": "#4cc9f0", "cyan": "#72efdd",
          "gold": "#ffca58", "orange": "#ff7b54", "pink": "#ef5da8"}
RNG = np.random.default_rng(1999)
"""


def notebook(title: str, archive: str, question: str, cells: list, sources: str):
    intro = f"""
# {title}

**Archive:** {archive}  
**Date:** {DATE}  
**Scientific question:** {question}

This notebook uses public observational data. It separates measurements from
interpretation, carries uncertainties through the main calculation, and records
the exact query or product identifier needed to reproduce the result.
"""
    standard = """
## Analysis contract

A result is accepted only after these checks:

1. record the source, query, retrieval date, and selection cuts;
2. inspect missing values and quality flags before fitting;
3. report sample size and an uncertainty, not only a best value;
4. compare with a published result or accepted physical expectation;
5. state what the data cannot establish.

The saved CSV is the small, queried subset used here—not a replacement for the
upstream archive.
"""
    end = f"""
## References and data acknowledgement

{sources}

The numerical results above are conditional on the documented cuts. Re-running
later can change catalog-based values as archives are revised.
"""
    nb = nbf.v4.new_notebook(
        cells=[md(intro), md(standard), code(COMMON_IMPORTS), *cells, md(end)],
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "colab": {"provenance": []},
        },
    )
    return nb


def write_case(archive: str, slug: str, nb, readme: str):
    folder = ROOT / archive / f"{DATE}-{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, folder / "notebook.ipynb")
    (folder / "README.md").write_text(readme.strip() + "\n", encoding="utf-8")


def hst_case():
    title = "HST/STIS spectrum of HD 93521: which atoms leave visible absorption lines?"
    slug = "hst-stis-hd93521-line-inventory"
    archive = "mast"
    question = "Which hydrogen and helium lines are measurable in a calibrated low-resolution HST spectrum?"
    cells = [
        md("""
## Why this target?

HD 93521 is a hot O-type star. Its optical spectrum should be dominated by
hydrogen and helium, making it a useful real-data test of line identification.
The aim is not to infer a full atmospheric abundance: one low-resolution
spectrum cannot do that. Instead, we measure line centres and equivalent widths,
then test whether they agree with expected H/He transitions.
"""),
        code("""
import requests
from astropy.io import fits
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit

DATA_URI = "mast:HST/product/o49x13010_sx1.fits"
DOWNLOAD = "https://mast.stsci.edu/api/v0.1/Download/file?uri=" + DATA_URI
fits_path = Path("o49x13010_sx1.fits")
if not fits_path.exists():
    response = requests.get(DOWNLOAD, timeout=120)
    response.raise_for_status()
    fits_path.write_bytes(response.content)

with fits.open(fits_path) as hdul:
    header = hdul[0].header.copy()
    row = hdul[1].data[0]
    wave = np.asarray(row["WAVELENGTH"], float)
    flux = np.asarray(row["FLUX"], float)
    error = np.asarray(row["ERROR"], float)
    dq = np.asarray(row["DQ"], int)

print(f"Product: {DATA_URI}")
print(f"Target={header['TARGNAME']}  Instrument={header['INSTRUME']}  "
      f"Grating={header['OPT_ELEM']}  exposure={header['TEXPTIME']:.1f} s")
print(f"Wavelength range: {wave.min():.1f}–{wave.max():.1f} Å; pixels={wave.size}")
"""),
        md("""
## Quality control

The STIS `sx1` file is already wavelength- and flux-calibrated. We retain only
finite, positive-uncertainty samples with a zero data-quality mask. Edge pixels
are excluded because the sensitivity and uncertainty are poor there.
"""),
        code("""
good = ((dq == 0) & np.isfinite(wave) & np.isfinite(flux) &
        np.isfinite(error) & (error > 0) & (wave > 5300) & (wave < 10000))
spec = pd.DataFrame({"wavelength_A": wave[good], "flux": flux[good], "error": error[good]})
spec.to_csv("spectrum_subset.csv", index=False)
snr = np.nanmedian(spec.flux / spec.error)
flagged_fraction = 1 - good.sum() / good.size
print(f"Usable samples: {good.sum()}/{good.size}; rejected fraction={flagged_fraction:.1%}")
print(f"Median per-pixel signal-to-noise ratio: {snr:.1f}")
"""),
        code("""
# A broad Savitzky–Golay curve estimates the local continuum without following narrow lines.
window = min(151, len(spec) // 2 * 2 - 1)
continuum = savgol_filter(spec.flux.to_numpy(), window, 2)
normalised = spec.flux.to_numpy() / continuum

fig, ax = plt.subplots(figsize=(12, 4.8))
ax.plot(spec.wavelength_A, normalised, color=COLORS["navy"], lw=1)
ax.axhline(1, color="0.5", ls="--", lw=1)
ax.set(xlabel="Vacuum wavelength (Å)", ylabel="Continuum-normalised flux",
       title="Calibrated HST/STIS G750L spectrum of HD 93521")
ax.set_ylim(0.45, 1.35)
fig.tight_layout()
fig.savefig("hd93521_normalised_spectrum.png", dpi=180)
plt.show()
"""),
        md("""
## Line measurement

For each expected transition, a straight local continuum plus a Gaussian
absorption profile is fitted over a fixed window. Equivalent width is then
integrated from the fitted normalised profile. The velocity is a diagnostic of
centering—not a precise stellar radial velocity—because G750L is low resolution
and broad stellar lines can be blended.
"""),
        code("""
line_list = {
    "He II 5411": 5411.52,
    "He I 5876": 5875.62,
    "H alpha 6563": 6562.80,
    "He I 6678": 6678.15,
    "He I 7065": 7065.19,
}

def absorption_model(x, c0, c1, depth, centre, sigma):
    return c0 + c1 * (x - centre) - depth * np.exp(-0.5 * ((x - centre) / sigma) ** 2)

measurements = []
for name, rest in line_list.items():
    width = 45 if name.startswith("H alpha") else 30
    keep = np.abs(spec.wavelength_A.to_numpy() - rest) < width
    x = spec.wavelength_A.to_numpy()[keep]
    y = normalised[keep]
    e = (spec.error.to_numpy() / continuum)[keep]
    p0 = [1.0, 0.0, max(0.03, 1 - np.nanmin(y)), x[np.nanargmin(y)], 6.0]
    bounds = ([0.7, -0.02, 0, rest - 20, 1],
              [1.3, 0.02, 1.0, rest + 20, 30])
    try:
        popt, pcov = curve_fit(absorption_model, x, y, p0=p0, sigma=e,
                               absolute_sigma=True, bounds=bounds, maxfev=30000)
        perr = np.sqrt(np.diag(pcov))
        grid = np.linspace(x.min(), x.max(), 1000)
        model = absorption_model(grid, *popt)
        local_cont = popt[0] + popt[1] * (grid - popt[3])
        ew = np.trapezoid(1 - model / local_cont, grid)
        velocity = 299792.458 * (popt[3] / rest - 1)
        measurements.append([name, rest, popt[3], perr[3], velocity, ew, popt[2], popt[4]])
    except Exception:
        measurements.append([name, rest, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])

lines = pd.DataFrame(measurements, columns=[
    "line", "rest_A", "centre_A", "centre_error_A", "velocity_km_s",
    "equivalent_width_A", "depth", "sigma_A"
])
lines.to_csv("line_measurements.csv", index=False)
lines.round(3)
"""),
        code("""
fig, axes = plt.subplots(2, 3, figsize=(13, 7.4))
for ax, (_, row) in zip(axes.flat, lines.iterrows()):
    rest = row.rest_A
    width = 45 if row.line.startswith("H alpha") else 30
    keep = np.abs(spec.wavelength_A.to_numpy() - rest) < width
    x = spec.wavelength_A.to_numpy()[keep]
    y = normalised[keep]
    ax.plot(x, y, color=COLORS["navy"], lw=1.2, label="STIS")
    if np.isfinite(row.centre_A):
        params = [1, 0, row.depth, row.centre_A, row.sigma_A]
        ax.plot(x, absorption_model(x, *params), color=COLORS["orange"], lw=2, label="fit")
    ax.axvline(rest, color=COLORS["blue"], ls="--", lw=1, label="laboratory")
    ax.set_title(f"{row.line}\\nEW={row.equivalent_width_A:.2f} Å")
    ax.set_xlabel("Wavelength (Å)")
    ax.set_ylim(max(0.35, np.nanmin(y) - .08), 1.18)
axes.flat[-1].axis("off")
handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.91, 0.08))
fig.suptitle("Local line fits: identity is supported by wavelength agreement", y=1.01)
fig.tight_layout()
fig.savefig("hd93521_line_fits.png", dpi=180, bbox_inches="tight")
plt.show()
"""),
        md("""
## Interpretation and limits

- Multiple hydrogen/helium features in one spectrum are stronger evidence than
  assigning an element from a single dip.
- Equivalent width measures line strength relative to the local continuum; it
  is not a direct abundance without an atmosphere model, temperature, gravity,
  rotation, and instrumental broadening.
- The fitted velocity is not promoted as a precision radial velocity. The
  broad G750L line-spread function and the star's rotationally broadened lines
  dominate the error budget.
"""),
        code("""
valid = lines.dropna()
median_abs_velocity = float(np.median(np.abs(valid.velocity_km_s)))
result = {
    "id": "2026-07-31-hst-stis-hd93521-line-inventory",
    "title": "HST/STIS chemical-line inventory of HD 93521",
    "archive": "MAST · HST",
    "date": "2026-07-31",
    "question": "Which hydrogen and helium lines are measurable in a calibrated HST spectrum?",
    "sample_size": int(good.sum()),
    "results": [
        f"{len(valid)} of {len(lines)} expected H/He features fitted",
        f"median spectrum S/N {snr:.1f} per usable pixel",
        f"Hα equivalent width {valid.loc[valid.line.str.startswith('H alpha'), 'equivalent_width_A'].iloc[0]:.2f} Å"
    ],
    "validation": "Line centres are checked against laboratory wavelengths; interpretation is limited to identification and equivalent width.",
    "notebook": "mast/2026-07-31-hst-stis-hd93521-line-inventory/notebook.ipynb",
    "hero": "mast/2026-07-31-hst-stis-hd93521-line-inventory/hd93521_normalised_spectrum.png",
    "tags": ["spectrum", "HST", "STIS", "chemistry"]
}
Path("result.json").write_text(json.dumps(result, indent=2))
print("\\nDashboard summary")
print("\\n".join("• " + x for x in result["results"]))
"""),
    ]
    sources = """
- HST product: `mast:HST/product/o49x13010_sx1.fits`
- STIS Data Handbook, STScI: https://hst-docs.stsci.edu/stisdhb
- MAST acknowledgement guidance: https://archive.stsci.edu/publishing/
- Atomic wavelengths should be cross-checked against the NIST Atomic Spectra Database:
  https://physics.nist.gov/asd
"""
    readme = f"""
# {title}

This analysis downloads a calibrated HST/STIS G750L spectrum from MAST, applies
the data-quality mask, estimates the continuum, and fits five expected hydrogen
or helium absorption features. It reports fitted centres, equivalent widths,
per-pixel signal-to-noise, and the exact MAST product URI.

The chemical claim is deliberately narrow: the wavelength pattern supports
line identification. It does **not** turn equivalent width into an elemental
abundance without a stellar-atmosphere model.

[Open the notebook](notebook.ipynb)
"""
    write_case(archive, slug, notebook(title, archive, question, cells, sources), readme)


def gaia_case():
    title = "Gaia DR3 Pleiades membership, distance, and colour–magnitude sequence"
    slug = "gaia-pleiades-membership-distance"
    archive = "gaia"
    question = "Can astrometry alone isolate the Pleiades and recover its mean distance?"
    cells = [
        md("""
## Physical idea

Members of an open cluster share a common motion and lie at nearly the same
distance. Gaia measures both proper-motion components and parallax, so the
Pleiades should appear as a compact three-dimensional group in
$(\\mu_{\\alpha*},\\mu_\\delta,\\varpi)$ space. A colour–magnitude diagram is an
independent sanity check: real members should trace a narrow stellar sequence.
"""),
        code("""
import requests

TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
QUERY = '''
SELECT TOP 10000 source_id, ra, dec, parallax, parallax_error,
       pmra, pmra_error, pmdec, pmdec_error,
       phot_g_mean_mag, bp_rp, ruwe
FROM gaiadr3.gaia_source
WHERE 1=CONTAINS(
  POINT('ICRS', ra, dec),
  CIRCLE('ICRS', 56.75, 24.1167, 1.5)
)
AND phot_g_mean_mag < 19
AND parallax BETWEEN 3 AND 12
AND pmra BETWEEN 10 AND 30
AND pmdec BETWEEN -55 AND -35
AND ruwe < 1.4
'''
params = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": QUERY}
response = requests.get(TAP, params=params, timeout=180)
response.raise_for_status()
stars = pd.read_csv(io.StringIO(response.text))
stars.to_csv("gaia_query.csv", index=False)
print(f"Retrieved {len(stars):,} quality-filtered sources")
print(f"Missing BP-RP colours: {stars.bp_rp.isna().mean():.1%}")
"""),
        md("""
## Membership model

The broad archive query removes very distant foreground/background stars and
poor single-star astrometric fits (`ruwe < 1.4`). Membership is then refined
with a robust covariance estimate in proper motion and parallax. This is a
transparent kinematic selection, not a complete membership catalogue.
"""),
        code("""
from sklearn.covariance import MinCovDet

features = stars[["pmra", "pmdec", "parallax"]].dropna()
robust = MinCovDet(random_state=1999, support_fraction=0.65).fit(features)
delta = features.to_numpy() - robust.location_
mahal2 = np.einsum("ij,jk,ik->i", delta, robust.precision_, delta)
stars["mahalanobis2"] = np.nan
stars.loc[features.index, "mahalanobis2"] = mahal2
stars["member"] = stars.mahalanobis2 < stats.chi2.ppf(0.997, df=3)
members = stars[stars.member & stars.bp_rp.notna()].copy()
members.to_csv("pleiades_members.csv", index=False)
print(f"Candidate members: {len(members)} ({len(members)/len(stars):.1%} of queried sample)")
print("Robust centre [pmRA, pmDec, parallax]:", robust.location_.round(3))
"""),
        code("""
fig, ax = plt.subplots(figsize=(7.5, 6.2))
ax.scatter(stars.pmra, stars.pmdec, s=8, c="0.78", alpha=.45, label="field/query sample")
sc = ax.scatter(members.pmra, members.pmdec, s=18, c=members.parallax,
                cmap="viridis", alpha=.85, label="kinematic candidates")
ax.scatter(robust.location_[0], robust.location_[1], marker="+", s=180,
           lw=2.5, color=COLORS["orange"], label="robust centre")
fig.colorbar(sc, ax=ax, label="Parallax (mas)")
ax.set(xlabel=r"$\\mu_{\\alpha*}$ (mas yr$^{-1}$)",
       ylabel=r"$\\mu_\\delta$ (mas yr$^{-1}$)",
       title="The Pleiades is a compact proper-motion group")
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig("pleiades_proper_motion.png", dpi=180)
plt.show()
"""),
        md("""
## Distance with uncertainty

For this nearby cluster the selected stars have high parallax signal-to-noise,
so inversion is a useful descriptive estimate. We calculate an
inverse-variance weighted mean parallax, its formal error, and a bootstrap
interval that also reflects finite-sample scatter. A publication-grade result
would model the Gaia parallax zero point and spatial covariance explicitly.
"""),
        code("""
high_snr = members[(members.parallax / members.parallax_error > 10) &
                   (members.parallax_error > 0)].copy()
w = 1 / high_snr.parallax_error**2
mean_plx = float(np.sum(w * high_snr.parallax) / np.sum(w))
formal_plx_err = float(np.sqrt(1 / np.sum(w)))
distance_pc = 1000 / mean_plx

boot = []
for _ in range(2000):
    sample = high_snr.sample(len(high_snr), replace=True, random_state=int(RNG.integers(1e9)))
    sw = 1 / sample.parallax_error**2
    boot.append(1000 / (sw @ sample.parallax / sw.sum()))
distance_ci = np.percentile(boot, [16, 84])
print(f"Weighted parallax = {mean_plx:.4f} ± {formal_plx_err:.4f} mas (formal)")
print(f"Descriptive distance = {distance_pc:.2f} pc")
print(f"Bootstrap 68% interval = [{distance_ci[0]:.2f}, {distance_ci[1]:.2f}] pc")
"""),
        code("""
members["absolute_g"] = members.phot_g_mean_mag + 5*np.log10(members.parallax) - 10
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].hist(1000/members.parallax, bins=35, color=COLORS["blue"], alpha=.8)
axes[0].axvline(distance_pc, color=COLORS["orange"], lw=2,
                label=f"weighted estimate {distance_pc:.1f} pc")
axes[0].set(xlabel="Inverse-parallax distance (pc)", ylabel="Candidates",
            title="Cluster distance distribution")
axes[0].legend()
axes[1].scatter(members.bp_rp, members.absolute_g, s=11, alpha=.65,
                c=members.mahalanobis2, cmap="magma_r")
axes[1].invert_yaxis()
axes[1].set(xlabel="Gaia BP − RP (mag)", ylabel=r"$M_G$ (mag)",
            title="Candidate members trace a narrow sequence")
fig.tight_layout()
fig.savefig("pleiades_distance_cmd.png", dpi=180)
plt.show()
"""),
        md("""
## Validation and limitations

The recovered distance should be close to the modern Gaia-era value of roughly
135–136 pc. Agreement validates the broad astrometric selection, but it does
not prove that every selected star is a member. The main unmodelled terms are
the Gaia parallax zero point, angular covariance, unresolved binaries, and the
selection imposed before robust fitting.
"""),
        code("""
literature_pc = 136.2
offset_pct = 100 * (distance_pc - literature_pc) / literature_pc
result = {
    "id": "2026-07-31-gaia-pleiades-membership-distance",
    "title": "Gaia DR3 Pleiades membership and distance",
    "archive": "Gaia DR3",
    "date": "2026-07-31",
    "question": "Can astrometry isolate the Pleiades and recover its distance?",
    "sample_size": int(len(stars)),
    "results": [
        f"{len(members)} kinematic candidates from {len(stars)} quality-filtered sources",
        f"weighted parallax {mean_plx:.3f} mas",
        f"distance {distance_pc:.1f} pc (bootstrap 68%: {distance_ci[0]:.1f}–{distance_ci[1]:.1f} pc)"
    ],
    "validation": f"Distance differs by {offset_pct:+.1f}% from the 136.2 pc comparison value; systematic Gaia terms are not included.",
    "notebook": "gaia/2026-07-31-gaia-pleiades-membership-distance/notebook.ipynb",
    "hero": "gaia/2026-07-31-gaia-pleiades-membership-distance/pleiades_proper_motion.png",
    "tags": ["astrometry", "cluster", "distance", "Gaia"]
}
Path("result.json").write_text(json.dumps(result, indent=2))
print("\\n".join("• " + x for x in result["results"]))
"""),
    ]
    sources = """
- Gaia DR3 archive table `gaiadr3.gaia_source`, queried through ESA TAP.
- Gaia Collaboration et al. (2017), *Gaia Data Release 1: Open cluster astrometry*,
  A&A 601, A19: https://doi.org/10.1051/0004-6361/201629392
- Gaia archive acknowledgement: https://www.cosmos.esa.int/web/gaia-users/credits
"""
    readme = f"""
# {title}

This notebook retrieves Gaia DR3 astrometry within 1.5° of the Pleiades,
performs a robust three-dimensional selection in proper motion and parallax,
measures a weighted cluster distance with a bootstrap interval, and checks the
selected stars against their colour–magnitude sequence.

The result is a transparent learning analysis, not a replacement for a
probabilistic membership catalogue. Gaia zero-point and spatial covariance
systematics are discussed rather than hidden.

[Open the notebook](notebook.ipynb)
"""
    write_case(archive, slug, notebook(title, archive, question, cells, sources), readme)


def sdss_case():
    title = "SDSS emission-line galaxies: star formation, composites, and AGN on the BPT diagram"
    slug = "sdss-bpt-galaxy-classification"
    archive = "sdss"
    question = "What fraction of a high-S/N low-redshift sample is dominated by star formation or an active nucleus?"
    cells = [
        md("""
## Diagnostic

The BPT diagram compares two pairs of nearby emission lines:
$\\log([\\mathrm{O III}]/H\\beta)$ and
$\\log([\\mathrm{N II}]/H\\alpha)$. Nearby wavelengths reduce sensitivity to
flux calibration and dust. The position reflects the hardness of the ionising
radiation field and separates star-forming galaxies from active galactic nuclei
(AGN), with an intermediate composite region.
"""),
        code("""
import requests

ENDPOINT = "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
QUERY = '''
SELECT TOP 12000 s.specObjID, s.ra, s.dec, s.z,
 l.h_alpha_flux, l.h_alpha_flux_err,
 l.h_beta_flux, l.h_beta_flux_err,
 l.oiii_5007_flux, l.oiii_5007_flux_err,
 l.nii_6584_flux, l.nii_6584_flux_err
FROM SpecObj AS s
JOIN galSpecLine AS l ON s.specObjID = l.specObjID
WHERE s.class = 'GALAXY' AND s.z BETWEEN 0.01 AND 0.20
AND l.h_alpha_flux > 5*l.h_alpha_flux_err
AND l.h_beta_flux > 5*l.h_beta_flux_err
AND l.oiii_5007_flux > 5*l.oiii_5007_flux_err
AND l.nii_6584_flux > 5*l.nii_6584_flux_err
'''
response = requests.get(ENDPOINT, params={"cmd": QUERY, "format": "csv"}, timeout=180)
response.raise_for_status()
text = response.text.replace("#Table1\\n", "", 1)
gal = pd.read_csv(io.StringIO(text))
gal.to_csv("sdss_bpt_query.csv", index=False)
print(f"Retrieved {len(gal):,} galaxies with S/N > 5 in all four lines")
print(f"Redshift range: {gal.z.min():.3f}–{gal.z.max():.3f}; median={gal.z.median():.3f}")
"""),
        md("""
## Ratios and dividing curves

We use the empirical Kauffmann et al. (2003) curve below which galaxies are
classified as star forming, and the theoretical maximum-starburst Kewley et
al. (2001) curve above which an AGN contribution is required. Objects between
the curves are labelled composite. These labels describe the fibre spectrum,
not necessarily the entire galaxy.
"""),
        code("""
gal["x"] = np.log10(gal.nii_6584_flux / gal.h_alpha_flux)
gal["y"] = np.log10(gal.oiii_5007_flux / gal.h_beta_flux)

def kauffmann(x):
    return 0.61/(x - 0.05) + 1.30

def kewley(x):
    return 0.61/(x - 0.47) + 1.19

sf = (gal.x < 0.05) & (gal.y < kauffmann(gal.x))
agn = (gal.x >= 0.47) | (gal.y >= kewley(gal.x))
gal["class_bpt"] = np.select([sf, agn], ["Star forming", "AGN"], default="Composite")
counts = gal.class_bpt.value_counts()
fractions = (counts / len(gal)).sort_index()
pd.DataFrame({"count": counts, "fraction": counts/len(gal)}).to_csv("bpt_class_fractions.csv")
pd.DataFrame({"count": counts, "fraction": counts/len(gal)}).round(4)
"""),
        code("""
xx1 = np.linspace(-2.0, 0.045, 500)
xx2 = np.linspace(-2.0, 0.465, 500)
palette = {"Star forming": COLORS["blue"], "Composite": COLORS["gold"], "AGN": COLORS["pink"]}
fig, ax = plt.subplots(figsize=(8.2, 7))
for label in ["Star forming", "Composite", "AGN"]:
    part = gal[gal.class_bpt == label]
    ax.scatter(part.x, part.y, s=7, alpha=.28, color=palette[label],
               rasterized=True, label=f"{label} ({len(part):,})")
ax.plot(xx1, kauffmann(xx1), color="black", lw=1.7, label="Kauffmann+03")
ax.plot(xx2, kewley(xx2), color="black", lw=1.7, ls="--", label="Kewley+01")
ax.set(xlim=(-1.8, .55), ylim=(-1.5, 1.6),
       xlabel=r"$\\log_{10}([N\\,II]\\,6584/H\\alpha)$",
       ylabel=r"$\\log_{10}([O\\,III]\\,5007/H\\beta)$",
       title="SDSS DR18 high-S/N emission-line galaxies")
ax.legend(markerscale=2, fontsize=9)
fig.tight_layout()
fig.savefig("sdss_bpt_diagram.png", dpi=190)
plt.show()
"""),
        md("""
## Fraction uncertainty

The sample is not volume-complete, so sampling uncertainty is not the dominant
scientific limitation. Still, Wilson binomial intervals quantify finite-count
uncertainty for the observed sample. The much larger systematic question is how
the four-line S/N cut favours strong emission-line galaxies.
"""),
        code("""
from statsmodels.stats.proportion import proportion_confint

interval_rows = []
for label, n in counts.items():
    lo, hi = proportion_confint(n, len(gal), alpha=0.05, method="wilson")
    interval_rows.append([label, n/len(gal), lo, hi])
intervals = pd.DataFrame(interval_rows, columns=["class", "fraction", "ci95_low", "ci95_high"])
intervals.round(4)
"""),
        md("""
## Balmer decrement as a dust indicator

Unobscured case-B recombination predicts $H\\alpha/H\\beta\\approx2.86$.
Larger ratios are commonly interpreted as dust reddening. Using a standard
Milky-Way attenuation curve gives an indicative colour excess. Negative values
are retained as noise/model scatter rather than silently clipped.
"""),
        code("""
k_hbeta, k_halpha = 3.61, 2.53
gal["balmer_decrement"] = gal.h_alpha_flux / gal.h_beta_flux
gal["ebv"] = 2.5/(k_hbeta-k_halpha) * np.log10(gal.balmer_decrement/2.86)
dust = gal.groupby("class_bpt").agg(
    n=("ebv", "size"),
    median_ebv=("ebv", "median"),
    median_balmer=("balmer_decrement", "median"),
    median_z=("z", "median")
)
dust.round(3)
"""),
        code("""
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
ordered = ["Star forming", "Composite", "AGN"]
axes[0].bar(ordered, [fractions[x] for x in ordered],
            color=[palette[x] for x in ordered])
axes[0].set(ylabel="Observed sample fraction", title="Classification mix")
for i, label in enumerate(ordered):
    vals = gal.loc[gal.class_bpt == label, "ebv"].clip(-.5, 2)
    axes[1].hist(vals, bins=45, histtype="step", density=True, lw=2,
                 color=palette[label], label=label)
axes[1].set(xlabel="Indicative E(B−V) from Balmer decrement",
            ylabel="Density", title="Dust indicator by BPT class")
axes[1].legend()
fig.tight_layout()
fig.savefig("sdss_bpt_summary.png", dpi=180)
plt.show()
"""),
        md("""
## What is established—and what is not

This notebook establishes the classification mix *within the selected
high-S/N fibre spectra*. It does not measure the cosmic AGN fraction: that
requires a defined parent sample, completeness corrections, aperture analysis,
and treatment of non-detections. Borderline sources also have classification
uncertainty because line-flux errors can move them across a curve.
"""),
        code("""
result = {
    "id": "2026-07-31-sdss-bpt-galaxy-classification",
    "title": "SDSS BPT galaxy classification",
    "archive": "SDSS DR18",
    "date": "2026-07-31",
    "question": "How are high-S/N low-redshift fibre spectra divided among ionisation classes?",
    "sample_size": int(len(gal)),
    "results": [
        f"{100*fractions['Star forming']:.1f}% star forming",
        f"{100*fractions['Composite']:.1f}% composite",
        f"{100*fractions['AGN']:.1f}% AGN within the four-line-selected sample"
    ],
    "validation": "Class boundaries reproduce the published Kauffmann (2003) and Kewley (2001) demarcations.",
    "notebook": "sdss/2026-07-31-sdss-bpt-galaxy-classification/notebook.ipynb",
    "hero": "sdss/2026-07-31-sdss-bpt-galaxy-classification/sdss_bpt_diagram.png",
    "tags": ["galaxies", "spectroscopy", "AGN", "emission lines"]
}
Path("result.json").write_text(json.dumps(result, indent=2))
print("\\n".join("• " + x for x in result["results"]))
"""),
    ]
    sources = """
- SDSS DR18 SkyServer `SpecObj` and `galSpecLine` tables:
  https://skyserver.sdss.org/dr18/
- Kewley et al. (2001), *Theoretical Modeling of Starburst Galaxies*:
  https://doi.org/10.1086/321545
- Kauffmann et al. (2003), *The host galaxies of active galactic nuclei*:
  https://doi.org/10.1046/j.1365-2966.2003.07154.x
- SDSS acknowledgement: https://www.sdss.org/collaboration/citing-sdss/
"""
    readme = f"""
# {title}

This notebook queries 12,000 low-redshift SDSS spectra with strong Hα, Hβ,
[O III], and [N II]. It constructs the BPT diagram, applies the published
Kauffmann and Kewley boundaries, reports Wilson intervals on the observed class
fractions, and compares Balmer-decrement dust indicators between classes.

The notebook clearly states that a four-line-selected sample cannot be used as
the cosmic AGN fraction without completeness corrections.

[Open the notebook](notebook.ipynb)
"""
    write_case(archive, slug, notebook(title, archive, question, cells, sources), readme)


def radius_valley_case():
    title = "Measuring the exoplanet radius valley from the NASA Exoplanet Archive"
    slug = "exoplanet-radius-valley"
    archive = "exoplanet-archive"
    question = "Is the scarcity of planets near 1.5–2 Earth radii visible in the current confirmed-planet catalogue?"
    cells = [
        md("""
## Scientific context

Close-in planets show two common size groups—roughly rocky super-Earths and
gas-rich sub-Neptunes—with a relative deficit between them. Photoevaporation
and core-powered mass loss can both create such a valley. Here we ask a narrower
catalogue question: where is the one-dimensional minimum for well-measured,
short-period transiting planets, and how stable is it to resampling?
"""),
        code("""
import requests
from scipy.signal import find_peaks
from scipy.stats import gaussian_kde

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
QUERY = '''
SELECT pl_name, hostname, disc_year, discoverymethod,
       pl_orbper, pl_rade, pl_radeerr1, pl_radeerr2,
       st_teff, st_rad
FROM pscomppars
WHERE tran_flag=1 AND pl_orbper IS NOT NULL AND pl_rade IS NOT NULL
'''
response = requests.get(TAP, params={"query": QUERY, "format": "csv"}, timeout=180)
response.raise_for_status()
planets = pd.read_csv(io.StringIO(response.text))
planets.to_csv("confirmed_transiting_planets.csv", index=False)
print(f"Archive rows retrieved: {len(planets):,}")
"""),
        md("""
## Selection

We restrict the measurement to 1–4 Earth radii and periods of 1–100 days, where
the two radius groups are most relevant. Radius errors must be reported and the
larger side of the asymmetric uncertainty must be below 20%. This improves
measurement quality but does not make the discovery sample complete.
"""),
        code("""
planets["radius_frac_error"] = (
    planets[["pl_radeerr1", "pl_radeerr2"]].abs().max(axis=1) / planets.pl_rade
)
sample = planets[
    planets.pl_rade.between(1, 4) &
    planets.pl_orbper.between(1, 100) &
    planets.radius_frac_error.between(0, .20)
].dropna(subset=["pl_rade", "pl_orbper"]).copy()
sample.to_csv("radius_valley_sample.csv", index=False)
print(f"Analysis sample: {len(sample):,} planets")
print(sample[["pl_orbper", "pl_rade", "radius_frac_error"]].describe().round(3))
"""),
        md("""
## Kernel-density estimate and bootstrap

A Gaussian kernel-density estimate smooths the discrete radius sample. We
identify the minimum between 1.4 and 2.2 Earth radii, then bootstrap planets
2,000 times. The interval describes sample sensitivity; bandwidth choice and
survey selection remain systematic uncertainties.
"""),
        code("""
grid = np.linspace(1.0, 4.0, 800)

def valley_location(radii):
    kde = gaussian_kde(radii, bw_method=0.18)
    density = kde(grid)
    zone = (grid >= 1.4) & (grid <= 2.2)
    return float(grid[zone][np.argmin(density[zone])]), density

valley, density = valley_location(sample.pl_rade.to_numpy())
boot_valleys = []
for _ in range(2000):
    draw = RNG.choice(sample.pl_rade.to_numpy(), len(sample), replace=True)
    try:
        boot_valleys.append(valley_location(draw)[0])
    except np.linalg.LinAlgError:
        pass
valley_ci = np.percentile(boot_valleys, [16, 84])
print(f"KDE radius valley = {valley:.3f} R_earth")
print(f"Bootstrap 68% interval = {valley_ci[0]:.3f}–{valley_ci[1]:.3f} R_earth")
"""),
        code("""
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
axes[0].hist(sample.pl_rade, bins=45, density=True, alpha=.35, color=COLORS["blue"])
axes[0].plot(grid, density, color=COLORS["navy"], lw=2.5)
axes[0].axvline(valley, color=COLORS["orange"], lw=2,
                label=f"minimum {valley:.2f} $R_\\oplus$")
axes[0].axvspan(*valley_ci, color=COLORS["orange"], alpha=.18, label="bootstrap 68%")
axes[0].set(xlabel=r"Planet radius ($R_\\oplus$)", ylabel="Density",
            title="Two radius groups and their intervening minimum")
axes[0].legend()
axes[1].hist(boot_valleys, bins=np.arange(1.38, 2.23, .025),
             color=COLORS["gold"], edgecolor="white")
axes[1].axvline(valley, color=COLORS["navy"], lw=2)
axes[1].set(xlabel=r"Bootstrap valley location ($R_\\oplus$)",
            ylabel="Resamples", title="Sampling stability")
fig.tight_layout()
fig.savefig("radius_valley_kde.png", dpi=180)
plt.show()
"""),
        md("""
## Period dependence

Published work finds that the valley is tilted in period–radius space rather
than perfectly horizontal. To avoid claiming more resolution than this
heterogeneous catalogue supports, we split the sample into four equal-width
bins in log period, measure the KDE minimum in each, and fit a line in
$\\log R$ versus $\\log P$.
"""),
        code("""
edges = np.logspace(0, 2, 5)
rows = []
for lo, hi in zip(edges[:-1], edges[1:]):
    part = sample[sample.pl_orbper.between(lo, hi, inclusive="left")]
    if len(part) >= 60:
        v, _ = valley_location(part.pl_rade.to_numpy())
        rows.append([np.sqrt(lo*hi), v, len(part)])
period_valleys = pd.DataFrame(rows, columns=["period_days", "valley_radius", "n"])
slope, intercept, r_value, p_value, slope_err = stats.linregress(
    np.log10(period_valleys.period_days), np.log10(period_valleys.valley_radius)
)
period_valleys["fit_radius"] = 10**(intercept + slope*np.log10(period_valleys.period_days))
period_valleys.to_csv("period_binned_valleys.csv", index=False)
print(period_valleys.round(3))
print(f"log-radius/log-period slope = {slope:+.3f} ± {slope_err:.3f}")
"""),
        code("""
fig, ax = plt.subplots(figsize=(8.3, 5.8))
sc = ax.scatter(sample.pl_orbper, sample.pl_rade, s=10, alpha=.28,
                c=sample.disc_year, cmap="viridis", rasterized=True)
ax.plot(period_valleys.period_days, period_valleys.fit_radius,
        color=COLORS["orange"], lw=3, label=f"binned-valley slope {slope:+.2f}")
ax.scatter(period_valleys.period_days, period_valleys.valley_radius,
           s=90, color="white", edgecolor=COLORS["navy"], zorder=4)
ax.set_xscale("log")
ax.set(xlabel="Orbital period (days)", ylabel=r"Planet radius ($R_\\oplus$)",
       ylim=(1, 4), title="Confirmed transiting planets in the valley regime")
fig.colorbar(sc, ax=ax, label="Discovery year")
ax.legend()
fig.tight_layout()
fig.savefig("radius_valley_period.png", dpi=180)
plt.show()
"""),
        md("""
## Comparison and limits

The expected literature valley lies roughly in the 1.5–2.0 Earth-radius range,
with its exact location depending on period and sample construction. Agreement
supports the implementation. It does not distinguish photoevaporation from
core-powered mass loss. A physical population inference needs survey detection
efficiencies, homogeneous stellar parameters, measurement posteriors, and a
forward model of the planet population.
"""),
        code("""
result = {
    "id": "2026-07-31-exoplanet-radius-valley",
    "title": "The exoplanet radius valley",
    "archive": "NASA Exoplanet Archive",
    "date": "2026-07-31",
    "question": "Where is the radius deficit in the current confirmed transiting-planet catalogue?",
    "sample_size": int(len(sample)),
    "results": [
        f"valley minimum {valley:.2f} Earth radii",
        f"bootstrap 68% interval {valley_ci[0]:.2f}–{valley_ci[1]:.2f} Earth radii",
        f"period–valley log slope {slope:+.2f} ± {slope_err:.2f}"
    ],
    "validation": "The measured minimum is compared with the published 1.5–2.0 Earth-radius valley; catalogue completeness is not modelled.",
    "notebook": "exoplanet-archive/2026-07-31-exoplanet-radius-valley/notebook.ipynb",
    "hero": "exoplanet-archive/2026-07-31-exoplanet-radius-valley/radius_valley_period.png",
    "tags": ["exoplanets", "population", "transits", "radius valley"]
}
Path("result.json").write_text(json.dumps(result, indent=2))
print("\\n".join("• " + x for x in result["results"]))
"""),
    ]
    sources = """
- NASA Exoplanet Archive `pscomppars` table:
  https://exoplanetarchive.ipac.caltech.edu/
- Fulton et al. (2017), *The California-Kepler Survey. III. A Gap in the Radius
  Distribution of Small Planets*: https://doi.org/10.3847/1538-3881/aa80eb
- Van Eylen et al. (2018), *An asteroseismic view of the radius valley*:
  https://doi.org/10.1093/mnras/sty1783
- Archive acknowledgement and DOI: https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html
"""
    readme = f"""
# {title}

This notebook downloads the current confirmed transiting-planet composite
table, applies explicit period/radius/precision cuts, locates the radius valley
with a kernel-density estimate, bootstraps its uncertainty, and measures a
coarse period dependence.

It validates the result against the published radius-valley range while
explaining why an uncorrected confirmed-planet catalogue cannot distinguish
competing atmospheric-loss mechanisms.

[Open the notebook](notebook.ipynb)
"""
    write_case(archive, slug, notebook(title, archive, question, cells, sources), readme)


def tidal_case():
    title = "Hot-Jupiter eccentricity and tidal circularisation in the NASA Exoplanet Archive"
    slug = "hot-jupiter-tidal-circularisation"
    archive = "exoplanet-archive"
    question = "Are short-period giant planets more circular than otherwise similar longer-period giants?"
    cells = [
        md("""
## Physical expectation

Tides dissipate orbital energy. Because tidal effects grow steeply at small
separation, close-in giant planets are expected to have lower eccentricities
than giants on wider orbits. We test that population-level expectation without
claiming to measure a tidal quality factor.
"""),
        code("""
import requests

TAP = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
QUERY = '''
SELECT pl_name, hostname, disc_year, discoverymethod,
       pl_orbper, pl_orbeccen, pl_orbeccenerr1, pl_orbeccenerr2,
       pl_radj, pl_bmassj, st_mass, st_teff
FROM pscomppars
WHERE pl_orbper IS NOT NULL AND pl_orbeccen IS NOT NULL
AND pl_radj IS NOT NULL
'''
response = requests.get(TAP, params={"query": QUERY, "format": "csv"}, timeout=180)
response.raise_for_status()
all_planets = pd.read_csv(io.StringIO(response.text))
all_planets.to_csv("giant_planet_archive_query.csv", index=False)
giants = all_planets[
    all_planets.pl_radj.between(0.6, 2.2) &
    all_planets.pl_orbper.between(0.5, 100) &
    all_planets.pl_orbeccen.between(0, 0.95)
].copy()
giants.to_csv("giant_planet_sample.csv", index=False)
print(f"Retrieved {len(all_planets):,} planets with period, radius, and eccentricity")
print(f"Analysis sample: {len(giants):,} giant planets")
"""),
        md("""
## Pre-registered comparison

We compare very hot giants ($P<5$ d) with giants at $10\\le P<100$ d. The gap
between 5 and 10 days reduces boundary sensitivity. We report medians,
bootstrap the median difference, and use a two-sided Mann–Whitney test. Archive
eccentricities include measurements, fitted zeros, and sometimes fixed values;
that heterogeneity is a major caveat.
"""),
        code("""
short = giants[giants.pl_orbper < 5].pl_orbeccen.to_numpy()
long = giants[giants.pl_orbper.between(10, 100, inclusive="left")].pl_orbeccen.to_numpy()
observed_delta = float(np.median(long) - np.median(short))
boot_delta = []
for _ in range(5000):
    a = RNG.choice(short, len(short), replace=True)
    b = RNG.choice(long, len(long), replace=True)
    boot_delta.append(np.median(b) - np.median(a))
delta_ci = np.percentile(boot_delta, [2.5, 97.5])
u = stats.mannwhitneyu(short, long, alternative="two-sided")
print(f"P < 5 d: n={len(short)}, median e={np.median(short):.3f}")
print(f"10 ≤ P < 100 d: n={len(long)}, median e={np.median(long):.3f}")
print(f"Median difference (long − short)={observed_delta:.3f}, "
      f"bootstrap 95% CI [{delta_ci[0]:.3f}, {delta_ci[1]:.3f}]")
print(f"Mann–Whitney U p={u.pvalue:.3g}")
"""),
        code("""
fig, ax = plt.subplots(figsize=(9, 5.8))
sc = ax.scatter(giants.pl_orbper, giants.pl_orbeccen, s=18, alpha=.45,
                c=giants.disc_year, cmap="viridis", rasterized=True)
ax.axvspan(.5, 5, color=COLORS["blue"], alpha=.10, label="short-period group")
ax.axvspan(10, 100, color=COLORS["gold"], alpha=.10, label="comparison group")
ax.set_xscale("log")
ax.set(xlabel="Orbital period (days)", ylabel="Published eccentricity",
       title="Close-in giant planets concentrate near circular orbits")
fig.colorbar(sc, ax=ax, label="Discovery year")
ax.legend()
fig.tight_layout()
fig.savefig("giant_eccentricity_period.png", dpi=180)
plt.show()
"""),
        md("""
## Eccentric fraction with Wilson intervals

Because an exact fitted zero and a small measured value do not have identical
meaning, we also use a coarse, interpretable threshold: the fraction with
$e>0.1$. Wilson intervals quantify the finite sample uncertainty.
"""),
        code("""
from statsmodels.stats.proportion import proportion_confint

groups = {"P < 5 d": short, "10 ≤ P < 100 d": long}
fraction_rows = []
for label, values in groups.items():
    k = int(np.sum(values > .1))
    lo, hi = proportion_confint(k, len(values), alpha=.05, method="wilson")
    fraction_rows.append([label, len(values), k/len(values), lo, hi])
ecc_fraction = pd.DataFrame(fraction_rows, columns=["group", "n", "fraction_e_gt_0p1", "ci95_low", "ci95_high"])
ecc_fraction.to_csv("eccentric_fraction.csv", index=False)
ecc_fraction.round(3)
"""),
        code("""
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
parts = axes[0].violinplot([short, long], positions=[0, 1],
                           showmedians=True, showextrema=False)
for body, color in zip(parts["bodies"], [COLORS["blue"], COLORS["gold"]]):
    body.set_facecolor(color); body.set_alpha(.7)
axes[0].set_xticks([0, 1], list(groups))
axes[0].set(ylabel="Published eccentricity", title="Distribution comparison")
axes[1].hist(boot_delta, bins=60, color=COLORS["cyan"], edgecolor="white")
axes[1].axvline(0, color="black", ls="--")
axes[1].axvline(observed_delta, color=COLORS["orange"], lw=2)
axes[1].set(xlabel="Bootstrap median difference (long − short)",
            ylabel="Resamples", title="Uncertainty in the median contrast")
fig.tight_layout()
fig.savefig("tidal_circularisation_test.png", dpi=180)
plt.show()
"""),
        md("""
## Sensitivity check

We repeat the median comparison for several short-period boundaries. A physical
trend should not depend on one exact cut. This is still descriptive: stellar
age, mass, radius, multiplicity, discovery method, and eccentricity reporting
all vary across the archive sample.
"""),
        code("""
checks = []
for boundary in [3, 4, 5, 6, 8]:
    a = giants[giants.pl_orbper < boundary].pl_orbeccen
    checks.append([boundary, len(a), a.median(), np.mean(a > .1)])
sensitivity = pd.DataFrame(checks, columns=["short_boundary_days", "n", "median_e", "fraction_e_gt_0p1"])
sensitivity.round(3)
"""),
        md("""
## Interpretation

A positive long-minus-short median difference and a much smaller $e>0.1$
fraction at short periods are consistent with tidal circularisation. They do
not show that tides alone produced every circular orbit, nor do they constrain
the tidal dissipation parameter without system ages and a hierarchical model.
Eccentricity measurements near zero are especially vulnerable to positive bias
and to catalogues mixing fixed and freely fitted values.
"""),
        code("""
short_frac = float(ecc_fraction.loc[ecc_fraction.group == "P < 5 d", "fraction_e_gt_0p1"].iloc[0])
long_frac = float(ecc_fraction.loc[ecc_fraction.group == "10 ≤ P < 100 d", "fraction_e_gt_0p1"].iloc[0])
result = {
    "id": "2026-07-31-hot-jupiter-tidal-circularisation",
    "title": "Hot-Jupiter tidal circularisation",
    "archive": "NASA Exoplanet Archive",
    "date": "2026-07-31",
    "question": "Are short-period giant planets more circular than longer-period giants?",
    "sample_size": int(len(giants)),
    "results": [
        f"median e={np.median(short):.3f} below 5 d versus {np.median(long):.3f} at 10–100 d",
        f"median contrast {observed_delta:.3f} (bootstrap 95%: {delta_ci[0]:.3f}–{delta_ci[1]:.3f})",
        f"e>0.1 fractions {100*short_frac:.1f}% versus {100*long_frac:.1f}%"
    ],
    "validation": "The direction of the period–eccentricity contrast matches the standard tidal-circularisation expectation.",
    "notebook": "exoplanet-archive/2026-07-31-hot-jupiter-tidal-circularisation/notebook.ipynb",
    "hero": "exoplanet-archive/2026-07-31-hot-jupiter-tidal-circularisation/giant_eccentricity_period.png",
    "tags": ["exoplanets", "dynamics", "tides", "hot Jupiters"]
}
Path("result.json").write_text(json.dumps(result, indent=2))
print("\\n".join("• " + x for x in result["results"]))
"""),
    ]
    sources = """
- NASA Exoplanet Archive `pscomppars` table:
  https://exoplanetarchive.ipac.caltech.edu/
- Winn et al. (2010), *Hot Stars with Hot Jupiters Have High Obliquities*,
  discussion of tidal timescales: https://doi.org/10.1088/2041-8205/718/2/L145
- Dawson & Johnson (2018), *Origins of Hot Jupiters*:
  https://doi.org/10.1146/annurev-astro-081817-051853
- Archive acknowledgement: https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html
"""
    readme = f"""
# {title}

This notebook selects confirmed giant planets with published periods,
eccentricities, and radii. It compares systems below 5 days with a 10–100 day
control range using medians, a 5,000-resample bootstrap, a rank test, Wilson
intervals for the fraction above e=0.1, and boundary sensitivity checks.

The result tests the expected direction of tidal circularisation without
over-claiming a tidal quality factor from a heterogeneous catalogue.

[Open the notebook](notebook.ipynb)
"""
    write_case(archive, slug, notebook(title, archive, question, cells, sources), readme)


def main():
    hst_case()
    gaia_case()
    sdss_case()
    radius_valley_case()
    tidal_case()
    print("Built five notebooks for", DATE)


if __name__ == "__main__":
    main()
