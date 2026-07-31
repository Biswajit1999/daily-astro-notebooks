<p align="center">
  <img src="assets/banner-animated.gif" alt="Animated Daily Astro Notebooks cover by Biswajit Jana, with illustrative Carina, Eagle and Ring Nebula artwork and a faint M87" width="100%">
</p>
<p align="center"><em>The animated cover is original illustrative artwork, not telescope data. Every scientific plot, spectrum, light curve, measurement, and object image inside <code>sdss/</code>, <code>mast/</code>, <code>gaia/</code>, and <code>exoplanet-archive/</code> is tied to the provenance and limits stated by its notebook.</em></p>

# Daily Astro Notebooks

**by Biswajit Jana**

<p>
  <a href="https://biswajit1999.github.io/daily-astro-notebooks/"><strong>Explore the notebook dashboard →</strong></a>
</p>

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

**55 notebooks, 4 archives, 3 observing-log dates — all 55 meet the deeper analysis standard, including 36 full scientific audits.**

The [dashboard](https://biswajit1999.github.io/daily-astro-notebooks/) is built from the repository itself. A new notebook appears there automatically after it is merged into `master` and the Pages workflow completes.

### Latest results

| Question | Data | Main result |
|---|---|---|
| Where is the small-planet radius valley? | NASA Exoplanet Archive, 2,070 planets | Minimum at **1.83 Earth radii**; 68% bootstrap range **1.80–1.86** |
| Are close-in giant planets more circular? | NASA Exoplanet Archive, 944 giants | Median eccentricity **0.000** below 5 days and **0.120** at 10–100 days |
| How far away is the Pleiades? | Gaia, 609 candidate members | Weighted parallax **7.374 mas**, giving **135.6 pc** |
| Which lines are present in an HST stellar spectrum? | HST/STIS spectrum of HD 93521 | All five tested H/He features recovered; H-alpha equivalent width **1.48 Å** |
| What powers the emission in nearby galaxies? | SDSS, 12,000 spectra | **73.1%** star-forming, **17.3%** composite, **9.6%** active-galaxy branch in the selected sample |
| How did SN 1987A's optical structures evolve? | HST imaging and published calibrated photometry | F625W ring flux fell **47.9%**, while ejecta flux rose **19.8%**, over the tabulated interval |
| Does SN 1987A look the same across JWST filters? | Four calibrated NIRCam images | The PSF-matched ring/ejecta ratio spans a factor of **4.14** from F150W to F444W |

### 50-notebook expansion

The newest 15 analyses deliberately include positive, negative, and method-limited results. Highlights include a hot-Jupiter radius–temperature rank correlation (**ρ = 0.558**), no detected Pleiades mass-segregation signal in the chosen angular sample (**permutation p = 0.619**), a Pleiades line-of-sight depth proxy of **2.16 pc**, an SDSS Balmer-decrement estimate of **E(B−V) = 0.327 mag**, and a demonstration that the H-alpha equivalent width changes by more than 100% across plausible continuum and integration choices in this low-resolution spectrum.

Four earlier notebooks were also repaired rather than merely given decorative images. TRAPPIST-1 and Kepler-442 b now have calculated orbital-zone figures. The Sirius and Vega notebooks now audit source identity against the Hipparcos catalogue; this corrects the earlier Vega cone-search mismatch that returned a background source while the prose described Vega's well-known nearby distance.

### Scientific Audit Batch 1

Five early MAST notebooks now expose multiple evidence figures, exact product
provenance, reusable tables, uncertainty or parameter stress tests, literature
context, and an explicit claim boundary. Kepler-10 b is recovered as a positive
remeasurement. TOI-700 d remains an exploratory null result when the simple
bootstrap interval includes zero. The selected Ring Nebula preview is also
labelled as a field mismatch rather than being used for a misleading shape
measurement. Negative results are preserved because they show exactly what the
current product or method cannot support.

### Scientific Audit Batch 2

Five more early notebooks now use exact saved archive products, multiple
evidence figures, reusable measurement tables, and explicit claim boundaries.
The most important correction is scientific rather than cosmetic: the product
previously described as a stellar spectrum is actually classified by SDSS as a
broad-line quasar, and the broad Balmer profiles support that identity. The
quasar redshift is now measured from C IV, C III], and Mg II instead of one
peak. The galaxy notebook jointly fits H-alpha and both [N II] lines and fixes a
factor-of-ten wavelength-unit error in the old velocity conversion.

The Kepler notebooks now use the full mission rather than one quarter.
Kepler-186 f is recovered at about **400 ppm** across ten covered transit
epochs using the verified DR25 ephemeris; its event-bootstrap 95% interval is
**375–468 ppm**. HAT-P-7 b returns a blind-search period of **2.205079 days**,
with an empirical shuffled-data false-alarm bound of **0.024** from 40 trials
and no significant odd/even depth disagreement. These are archive
remeasurements, not new planet validations.

### Scientific Audit Batch 3

Five connected notebooks turn SN 1987A into a time-domain and multi-wavelength
case study. Six official Hubble frames from 1994–2006 are registered and saved
as an animation, but their processed display pixels are used only for visible
structure. A separate notebook reanalyses calibrated HST measurements: the
F625W equatorial-ring flux falls **47.9%**, while the ejecta rises **19.8%**
between days 8717 and 12598. Keeping those two jobs separate prevents a display
image from being mistaken for a light curve.

Four calibrated JWST/NIRCam products are preserved as compact FITS cutouts with
their units and celestial coordinates. One notebook constructs a documented
false-colour RGB image from F150W, F200W, and F444W. Another aligns all four
filters, approximately matches their image sharpness, subtracts local
background, and repeats the aperture measurement across nine choices. The
ring/ejecta ratio changes by a factor of **4.14**, with the largest measured
ratio in F356W. Broad-filter colours are not presented as chemical abundances.

The final notebook registers HST F625W from 2018 against JWST F200W from 2022.
The normalized intensity correlation is **0.921** at a 0.12-arcsecond common
resolution, but it remains an exploratory structure comparison because the
filters, epochs, and telescopes differ.

### Scientific Audit Batch 4 — Gaia clusters and a repaired null result

The Pleiades and NGC 188 notebooks now retain source-level quality cuts,
membership-threshold tests, uncertainty, and reusable tables. The Pleiades
quality sample gives a median inverse-parallax distance of **136.04 pc**. The
NGC 188 high-probability sample gives a median parallax of **0.528 mas**. The
Hyades and M67 first-day plots did not preserve their source rows, so their new
notebooks honestly audit the saved figures instead of inventing missing stars.
The Alpha Centauri null result is repaired: Proxima is **2.21°** from the
approximate cone centre and was outside the original 2° search, so zero rows
never constrained wide companions.

### Scientific Audit Batch 5 — exoplanet populations and RV models

Five archive notebooks now separate geometry from observation and selection
from physics. The calculated transit-depth scaling approaches the expected
square law only when host-star radius is narrowed. The mass–period correlation
is almost absent for transit discoveries (**ρ = 0.029**) but strong within the
radial-velocity subset (**ρ = 0.714**), demonstrating method dependence. The
long-minus-short-period median eccentricity contrast is **0.160** with a
bootstrap 95% interval of **0.149–0.180**. The 51 Peg b and HD 189733 b curves
are now labelled archive-orbit reconstructions rather than observed RV data.

### Scientific Audit Batch 6 — SDSS evidence and legacy-output recovery

The galaxy redshift slice now uses 12,000 preserved source rows and exposes its
strongest redshift concentrations with an RA jackknife. Four older notebooks
had saved only aggregate counts or plots. Their revisions explicitly digitize
the retained evidence, stress the digitization choice, and reject catalogue-
level precision. This preserves useful findings—such as the reported weak
metallicity–latitude correlation—without pretending that rendered pixels are
independent spectra or stars.

### Scientific Audit Batch 7 — HST field-placement check

The early M87 preview is now an image-completeness audit. M87 reaches the frame
boundary at every tested threshold, and the bottom-edge bright-pixel fraction
reaches **12.5%**. Morphology, photometry, and jet measurements are therefore
rejected for this preview; the notebook states that a target-centred calibrated
FITS product is the required next observation.

### Scientific Audit Batch 8 — HST spectroscopy, M87 limits, and the radius valley

Five already-dense notebooks now carry the full audit contract. Three connected
HST/STIS studies of HD 93521 separate feature identification, an empirical
continuum slope, and H-alpha equivalent-width systematics. The added tests show
that formal flux-noise uncertainty is smaller than the change caused by
continuum and integration choices. Hydrogen and helium feature identification
is therefore not presented as a chemical-abundance or stellar-atmosphere fit.

The M87 display-image notebook now exposes its threshold dependence and rejects
calibrated morphology claims because the object reaches the preview boundary.
The exoplanet radius-valley notebook retains its **1.83 Earth-radius** minimum
and period slope of **−0.13 ± 0.04**, while explicitly separating a catalogue
deficit from an occurrence-rate measurement. Survey completeness is not
modelled here.

Reusable outputs declared by audited notebooks are indexed with file sizes and
SHA-256 checksums in [`DATA_PRODUCTS.json`](DATA_PRODUCTS.json). Project citation
metadata are available in [`CITATION.cff`](CITATION.cff).

<details>
<summary><b>sdss/</b> — 13 notebooks</summary>

- [`star-spectrum-classification`](sdss/2026-07-30-star-spectrum-classification/) — correcting a source mismatch: the exact product is a broad-line quasar, not a star
- [`qso-redshift-check`](sdss/2026-07-30-qso-redshift-check/) — measuring a quasar redshift from three broad emission lines with uncertainty
- [`emission-line-measurement`](sdss/2026-07-30-emission-line-measurement/) — jointly fitting H-alpha and [N II], with bootstrap and window checks
- [`metallicity-vs-position`](sdss/2026-07-30-metallicity-vs-position/) — stellar metallicity vs. position in the galaxy
- [`spectral-type-distribution`](sdss/2026-07-30-spectral-type-distribution/) — how spectral types are distributed across a sample
- [`white-dwarf-spectrum`](sdss/2026-07-30-white-dwarf-spectrum/) — looking at a white dwarf's spectrum
- [`galaxy-redshift-slice`](sdss/2026-07-30-galaxy-redshift-slice/) — a redshift "cone diagram" slice of galaxies
- [`qso-vs-galaxy-colors`](sdss/2026-07-30-qso-vs-galaxy-colors/) — telling quasars and galaxies apart by color
- [`sdss-bpt-galaxy-classification`](sdss/2026-07-31-sdss-bpt-galaxy-classification/) — separating star-forming, composite, and active galaxies with four emission lines
- [`balmer-decrement-dust`](sdss/2026-07-31-balmer-decrement-dust/) — estimating a nebular dust indicator from H-alpha and H-beta
- [`n2-metallicity-proxy`](sdss/2026-07-31-n2-metallicity-proxy/) — measuring an approximate oxygen-abundance distribution on the star-forming branch
- [`excitation-redshift-selection`](sdss/2026-07-31-excitation-redshift-selection/) — testing how the observed [O III]/H-beta ratio changes with redshift and selection
- [`bpt-snr-sensitivity`](sdss/2026-07-31-bpt-snr-sensitivity/) — quantifying how line-quality cuts move BPT class fractions

</details>

<details>
<summary><b>mast/</b> — 17 notebooks</summary>

- [`jwst-image-carina-nebula`](mast/2026-07-30-jwst-image-carina-nebula/) — real JWST NIRCam image of the Carina Nebula
- [`hst-image-eagle-nebula`](mast/2026-07-30-hst-image-eagle-nebula/) — Hubble image of the Eagle Nebula (Pillars of Creation)
- [`jwst-image-ring-nebula`](mast/2026-07-30-jwst-image-ring-nebula/) — real JWST image of the Ring Nebula
- [`hst-cutout-m87`](mast/2026-07-30-hst-cutout-m87/) — Hubble cutout of the M87 galaxy
- [`kepler-lightcurve-kepler10b`](mast/2026-07-30-kepler-lightcurve-kepler10b/) — Kepler-10b transit light curve
- [`kepler-lightcurve-kepler186f`](mast/2026-07-30-kepler-lightcurve-kepler186f/) — full-mission Kepler-186 f coverage, event bootstrap, and injection recovery
- [`tess-lightcurve-toi700`](mast/2026-07-30-tess-lightcurve-toi700/) — TESS light curve for TOI-700 d
- [`periodogram-hat-p-7b`](mast/2026-07-30-periodogram-hat-p-7b/) — HAT-P-7 b period search, false-alarm test, and odd/even audit
- [`hst-stis-hd93521-line-inventory`](mast/2026-07-31-hst-stis-hd93521-line-inventory/) — fitting hydrogen and helium features in a calibrated Hubble spectrum
- [`hst-stis-continuum-slope`](mast/2026-07-31-hst-stis-continuum-slope/) — fitting an empirical power law to the line-masked optical continuum
- [`hst-halpha-equivalent-width-systematics`](mast/2026-07-31-hst-halpha-equivalent-width-systematics/) — measuring how continuum and integration choices change H-alpha equivalent width
- [`hst-m87-image-morphology`](mast/2026-07-31-hst-m87-image-morphology/) — measuring display-image centroid, axis ratio, and half-light-radius proxies without claiming calibrated photometry
- [`hst-sn1987a-timelapse`](mast/2026-08-01-hst-sn1987a-timelapse/) — registering six official Hubble frames and building a 1994–2006 animation
- [`hst-sn1987a-lightcurve`](mast/2026-08-01-hst-sn1987a-lightcurve/) — reanalysing calibrated ring, ejecta, and centre fluxes with uncertainty
- [`jwst-sn1987a-rgb`](mast/2026-08-01-jwst-sn1987a-rgb/) — reconstructing a documented three-filter NIRCam false-colour image
- [`jwst-sn1987a-filter-morphology`](mast/2026-08-01-jwst-sn1987a-filter-morphology/) — PSF-matching four filters and testing the ring/ejecta ratio across apertures
- [`hst-jwst-sn1987a-comparison`](mast/2026-08-01-hst-jwst-sn1987a-comparison/) — comparing registered normalized structure across HST and JWST with explicit limits

</details>

<details>
<summary><b>gaia/</b> — 12 notebooks</summary>

- [`hr-diagram-pleiades`](gaia/2026-07-30-hr-diagram-pleiades/) — HR diagram of the Pleiades
- [`hr-diagram-hyades`](gaia/2026-07-30-hr-diagram-hyades/) — HR diagram of the Hyades
- [`hr-diagram-ngc188`](gaia/2026-07-30-hr-diagram-ngc188/) — HR diagram of open cluster NGC 188
- [`proper-motion-membership-m67`](gaia/2026-07-30-proper-motion-membership-m67/) — finding true M67 members by proper motion
- [`parallax-distance-vega`](gaia/2026-07-30-parallax-distance-vega/) — distance to Vega from its parallax
- [`parallax-distance-sirius`](gaia/2026-07-30-parallax-distance-sirius/) — distance to Sirius from its parallax
- [`wide-binary-search-alpha-cen`](gaia/2026-07-30-wide-binary-search-alpha-cen/) — looking for wide binary companions near Alpha Centauri
- [`gaia-pleiades-membership-distance`](gaia/2026-07-31-gaia-pleiades-membership-distance/) — selecting Pleiades members and measuring a bootstrap-tested cluster distance
- [`pleiades-cmd-ruwe-binaries`](gaia/2026-07-31-pleiades-cmd-ruwe-binaries/) — testing whether over-luminous sequence outliers also have poorer astrometric fits
- [`pleiades-mass-segregation-proxy`](gaia/2026-07-31-pleiades-mass-segregation-proxy/) — checking whether brighter members are more centrally concentrated
- [`pleiades-proper-motion-dispersion`](gaia/2026-07-31-pleiades-proper-motion-dispersion/) — subtracting reported measurement errors from the cluster motion width
- [`pleiades-line-of-sight-depth`](gaia/2026-07-31-pleiades-line-of-sight-depth/) — testing whether the parallax width exceeds formal errors

</details>

<details>
<summary><b>exoplanet-archive/</b> — 13 notebooks</summary>

- [`transit-depth-vs-radius`](exoplanet-archive/2026-07-30-transit-depth-vs-radius/) — transit depth vs. planet radius across confirmed planets
- [`habitable-zone-trappist1`](exoplanet-archive/2026-07-30-habitable-zone-trappist1/) — checking which TRAPPIST-1 planets fall in the habitable zone
- [`habitable-zone-kepler442`](exoplanet-archive/2026-07-30-habitable-zone-kepler442/) — habitable-zone check for Kepler-442
- [`rv-curve-51-pegasi-b`](exoplanet-archive/2026-07-30-rv-curve-51-pegasi-b/) — radial-velocity curve for 51 Pegasi b, the first exoplanet found around a Sun-like star
- [`rv-curve-hd189733b`](exoplanet-archive/2026-07-30-rv-curve-hd189733b/) — radial-velocity curve for HD 189733 b
- [`mass-period-trend`](exoplanet-archive/2026-07-30-mass-period-trend/) — how planet mass trends with orbital period
- [`eccentricity-distribution`](exoplanet-archive/2026-07-30-eccentricity-distribution/) — how eccentric confirmed planet orbits actually are
- [`exoplanet-radius-valley`](exoplanet-archive/2026-07-31-exoplanet-radius-valley/) — locating the scarcity of planets between super-Earths and sub-Neptunes
- [`hot-jupiter-tidal-circularisation`](exoplanet-archive/2026-07-31-hot-jupiter-tidal-circularisation/) — testing how giant-planet eccentricity changes with orbital period
- [`exoplanet-discovery-method-timeline`](exoplanet-archive/2026-07-31-exoplanet-discovery-method-timeline/) — tracing how the archive's discovery-method mixture changed over time
- [`hot-jupiter-radius-inflation`](exoplanet-archive/2026-07-31-hot-jupiter-radius-inflation/) — testing the giant-planet radius relation with host temperature
- [`eccentricity-discovery-bias`](exoplanet-archive/2026-07-31-eccentricity-discovery-bias/) — comparing recorded eccentricities across discovery channels
- [`single-vs-multiplanet-systems`](exoplanet-archive/2026-07-31-single-vs-multiplanet-systems/) — comparing radii around single- and multi-transiting hosts

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

The deeper notebooks also state a testable question, record the exact sample cuts, attach uncertainty to the main number, check at least one possible bias, and compare the result with published work. See the full [notebook analysis standard](NOTEBOOK_STANDARD.md).

## Reproduce the work

```bash
python -m pip install -r requirements.txt
python tools/run_notebooks.py --date 2026-07-31
python tools/validate_repository.py
```

To rebuild the dashboard catalogue and site locally:

```bash
python tools/build_catalog.py
cd dashboard
npm install
npm run dev
```

Contribution guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).

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
