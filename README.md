<p align="center">
  <img src="assets/banner.png" alt="Daily Astro Notebooks by Biswajit — title banner over the Carina Nebula, Eagle Nebula, and Ring Nebula" width="100%">
</p>
<p align="center"><em>This title banner is an AI-generated stylized composite for decoration only. The actual science in this repo is not: every plot, spectrum, light curve, and image inside <code>sdss/</code>, <code>mast/</code>, <code>gaia/</code>, and <code>exoplanet-archive/</code> is real archive data, pulled and processed by the notebooks themselves — see the real JWST/HST captures directly in <a href="mast/"><code>mast/</code></a>.</em></p>

# Daily Astro Notebooks

**by Biswajit**

A running, dated log of real-data astronomy analysis. Every day I add new
notebooks under one of the four archive folders below, using actual public
data — real spectra, real telescope images, real light curves, real catalog
queries. No toy or simulated data, ever, unless a notebook says so explicitly
(and even then it's clearly labeled).

Each notebook is written to run in Google Colab: open it straight from GitHub
using the "Open in Colab" badge at the top of the notebook — no download,
no setup, just run it.

## Why this exists

I wanted a public, dated paper trail of hands-on data analysis across the
big public astronomy archives — not tutorials I've only read, but notebooks
I've actually run against real data, with real output baked in. It's part
practice, part portfolio, part just wanting to look at real telescope data
every day instead of talking about it.

## Folders

| Folder | Archive | What's in it |
|---|---|---|
| [`sdss/`](sdss/) | Sloan Digital Sky Survey | Stellar and quasar spectra, redshifts, metallicities, spectral classification — via `astropy` + `astroquery.sdss` / direct FITS reads |
| [`mast/`](mast/) | MAST (Hubble, JWST, Kepler, TESS) | Real telescope images of nebulae and galaxies, exoplanet-host light curves, transit periodograms — via `astroquery.mast` + `lightkurve` |
| [`gaia/`](gaia/) | ESA Gaia | HR diagrams, cluster membership by proper motion, parallax-based distances, wide binaries — via `astroquery.gaia` (TAP) |
| [`exoplanet-archive/`](exoplanet-archive/) | NASA Exoplanet Archive | Transit depth vs. radius, habitable-zone checks, radial-velocity curves, mass–period trends — via TAP queries |

Each dated subfolder contains:

- `notebook.ipynb` — the analysis, run end-to-end with real output baked in
  (printed values, real plots — not just code)
- `README.md` — a short, plain-language writeup: what I looked at, what I
  found, what surprised me
- any small plot/image files the notebook produced

## What's here so far

**30 notebooks, 4 archives, 1 day of backfill (2026-07-30) — one new batch every day going forward.**

<details>
<summary><b>sdss/</b> — 8 notebooks</summary>

- [`star-spectrum-classification`](sdss/2026-07-30-star-spectrum-classification/) — classifying a star from its raw spectrum
- [`qso-redshift-check`](sdss/2026-07-30-qso-redshift-check/) — measuring a quasar's redshift from its emission lines
- [`emission-line-measurement`](sdss/2026-07-30-emission-line-measurement/) — measuring an H-alpha emission line
- [`metallicity-vs-position`](sdss/2026-07-30-metallicity-vs-position/) — stellar metallicity vs. position in the galaxy
- [`spectral-type-distribution`](sdss/2026-07-30-spectral-type-distribution/) — how spectral types are distributed across a sample
- [`white-dwarf-spectrum`](sdss/2026-07-30-white-dwarf-spectrum/) — looking at a white dwarf's spectrum
- [`galaxy-redshift-slice`](sdss/2026-07-30-galaxy-redshift-slice/) — a redshift "cone diagram" slice of galaxies
- [`qso-vs-galaxy-colors`](sdss/2026-07-30-qso-vs-galaxy-colors/) — telling quasars and galaxies apart by color

</details>

<details>
<summary><b>mast/</b> — 8 notebooks</summary>

- [`jwst-image-carina-nebula`](mast/2026-07-30-jwst-image-carina-nebula/) — real JWST NIRCam image of the Carina Nebula
- [`hst-image-eagle-nebula`](mast/2026-07-30-hst-image-eagle-nebula/) — Hubble image of the Eagle Nebula (Pillars of Creation)
- [`jwst-image-ring-nebula`](mast/2026-07-30-jwst-image-ring-nebula/) — real JWST image of the Ring Nebula
- [`hst-cutout-m87`](mast/2026-07-30-hst-cutout-m87/) — Hubble cutout of the M87 galaxy
- [`kepler-lightcurve-kepler10b`](mast/2026-07-30-kepler-lightcurve-kepler10b/) — Kepler-10b transit light curve
- [`kepler-lightcurve-kepler186f`](mast/2026-07-30-kepler-lightcurve-kepler186f/) — Kepler-186f transit light curve
- [`tess-lightcurve-toi700`](mast/2026-07-30-tess-lightcurve-toi700/) — TESS light curve for TOI-700 d
- [`periodogram-hat-p-7b`](mast/2026-07-30-periodogram-hat-p-7b/) — box-least-squares transit search for HAT-P-7b

</details>

<details>
<summary><b>gaia/</b> — 7 notebooks</summary>

- [`hr-diagram-pleiades`](gaia/2026-07-30-hr-diagram-pleiades/) — HR diagram of the Pleiades
- [`hr-diagram-hyades`](gaia/2026-07-30-hr-diagram-hyades/) — HR diagram of the Hyades
- [`hr-diagram-ngc188`](gaia/2026-07-30-hr-diagram-ngc188/) — HR diagram of open cluster NGC 188
- [`proper-motion-membership-m67`](gaia/2026-07-30-proper-motion-membership-m67/) — finding true M67 members by proper motion
- [`parallax-distance-vega`](gaia/2026-07-30-parallax-distance-vega/) — distance to Vega from its parallax
- [`parallax-distance-sirius`](gaia/2026-07-30-parallax-distance-sirius/) — distance to Sirius from its parallax
- [`wide-binary-search-alpha-cen`](gaia/2026-07-30-wide-binary-search-alpha-cen/) — looking for wide binary companions near Alpha Centauri

</details>

<details>
<summary><b>exoplanet-archive/</b> — 7 notebooks</summary>

- [`transit-depth-vs-radius`](exoplanet-archive/2026-07-30-transit-depth-vs-radius/) — transit depth vs. planet radius across confirmed planets
- [`habitable-zone-trappist1`](exoplanet-archive/2026-07-30-habitable-zone-trappist1/) — checking which TRAPPIST-1 planets fall in the habitable zone
- [`habitable-zone-kepler442`](exoplanet-archive/2026-07-30-habitable-zone-kepler442/) — habitable-zone check for Kepler-442
- [`rv-curve-51-pegasi-b`](exoplanet-archive/2026-07-30-rv-curve-51-pegasi-b/) — radial-velocity curve for 51 Pegasi b, the first exoplanet found around a Sun-like star
- [`rv-curve-hd189733b`](exoplanet-archive/2026-07-30-rv-curve-hd189733b/) — radial-velocity curve for HD 189733 b
- [`mass-period-trend`](exoplanet-archive/2026-07-30-mass-period-trend/) — how planet mass trends with orbital period
- [`eccentricity-distribution`](exoplanet-archive/2026-07-30-eccentricity-distribution/) — how eccentric confirmed planet orbits actually are

</details>

## How I work

1. Pick a real, specific target or question — not "explore Gaia data," but
   "how far away is Vega, using its actual parallax."
2. Query the real archive (`astroquery`, `sdss_access`, or a direct TAP/HTTP
   call) — no cached fake data, no placeholder plots.
3. Run the notebook top to bottom so the checked-in `.ipynb` already has the
   real output in it — anyone opening it in Colab sees exactly what I saw.
4. Write the README in plain language, like I'm explaining it to a friend
   who isn't an astronomer — technical terms get defined the first time
   they show up, not assumed.

## Tools used

`astropy` · `astroquery` (`.mast`, `.gaia`, `.sdss`) · `lightkurve` · `pyvo`
· `numpy` / `matplotlib` · `sdss_access`

## Citing the data

Every notebook closes with a citation for the archive it pulled from. As a
general rule:

- SDSS — [sdss.org/collaboration/citing-sdss](https://www.sdss.org/collaboration/citing-sdss/)
- MAST — [archive.stsci.edu/publishing](https://archive.stsci.edu/publishing/)
- Gaia — [cosmos.esa.int/web/gaia-users/credits](https://www.cosmos.esa.int/web/gaia-users/credits)
- NASA Exoplanet Archive — [exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html](https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html)

---

Maintained by **Biswajit** ([@Biswajit1999](https://github.com/Biswajit1999)).
New real-data notebooks added daily.
