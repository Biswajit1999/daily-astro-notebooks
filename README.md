# Daily Astro Notebooks

A running log of small, real-data astronomy analyses. Every day I add a new
dated notebook (or a few) under one of the four archive folders below, using
actual public data — real spectra, real telescope images, real catalogs. No
toy/simulated data unless a notebook says so explicitly.

Each notebook is written to run in Google Colab: open it straight from GitHub
using the "Open in Colab" badge at the top of the notebook, no download needed.

## Folders

- **`sdss/`** — Sloan Digital Sky Survey (DR20) spectra: stellar, quasar, and
  survey-target analyses using `astropy` + `sdss_access` / direct FITS reads.
- **`mast/`** — Mikulski Archive for Space Telescopes: Hubble, JWST, Kepler,
  and TESS images and light curves, via `astroquery.mast`.
- **`gaia/`** — ESA Gaia archive: astrometry, photometry, HR diagrams, and
  stellar population work, via `astroquery.gaia`.
- **`exoplanet-archive/`** — NASA Exoplanet Archive: transit light curves,
  radial velocity data, planet parameter tables, via `astroquery` /
  `pyvo` TAP queries.

Each dated subfolder contains:

- `notebook.ipynb` — the analysis, written and run end-to-end with real
  output baked in
- `README.md` — a short plain-language writeup of what I looked at, what I
  found, and anything that surprised me
- any small data/plot files the notebook produces

## Why

I'm building this up as a public, dated record of hands-on data analysis
across the major public astronomy archives — practice, portfolio, and a
paper trail of what I've actually looked at.
