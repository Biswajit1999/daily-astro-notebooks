# 2026-11-23 — Deep-visit flux repeatability near the detection threshold

Biswajit Jana | Science day: **unassigned** | Status: **archive intake blocked; no observational inference**

## Prior work and literature screen
Before defining this project, inspected `RESEARCH_INDEX.md` on `master`, the research-branch Euclid README and existing run updates (19–22 November). Earlier work already addresses Fornax colour outliers, EDF-North compact doubles across visits, cluster spectroscopy, and NGC 1291 ring imaging. This test instead targets **population-level flux repeatability in deep-mode visit products**, not individual compact-pair colour reversal. Screened the ESA DR1-Foundation explanatory supplement (12 November 2026), IRSA DR1 overview and 18 November archive access guide, the Euclid Q1 overview paper, and selected current DR1 literature. This is a bounded release/documentation and selected-publication screen, **not** a complete ADS/arXiv novelty search. Do not claim an unstudied effect.

Sources:
- https://euclid.esac.esa.int/dr/dr1/expsup/master.html
- https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html
- https://irsa.ipac.caltech.edu/euclid-archive-documentation/data-access/
- https://doi.org/10.26131/IRSA677 (MER deep visits)
- https://doi.org/10.1051/0004-6361/202554610 (Q1 overview)

## Preregistered, distinct falsifiable test — **Does the faint end of Euclid deep-visit photometry show excess repeatability scatter?**
Use a finite **single verified deep-mode tile** chosen by lowest available numeric tile ID with >=2 visits and at least 200 unmasked sources; freeze its tile ID and observed footprint before extracting measurements. This tile-selection rule is prospective and has not yet been executed. Use only public DR1-F MER deep-mode and photometry rows. Identify exact ID, visit, flux, uncertainty, flag and coordinate column names/units from TAP_SCHEMA; fail closed if the schema cannot support a valid source/visit join. Require >=2 valid visit measurements per unique source and positive quoted uncertainty. Do not mistake multiple detections in the same visit for independent epochs.

Primary comparison: within-visit flux signal-to-noise bins 5–10 versus 20–50, with matched source morphology and sky-background strata where available. For source i, visit j, estimate inverse-variance mean flux and standardized residual (f_ij - mean_i)/sigma_ij, accounting for uncertainty in the fitted mean and correlated calibration where documented. Compare robust MAD-based residual scatter, bootstrap resampling **by source** (not visit), and a preregistered 95% interval on the faint-minus-bright difference. Report the null when interval overlaps zero. Flag variable/moving Gaia objects, blends, diffraction, persistence, saturation, bad pixels, duplicated catalogue IDs, visit zeropoint offsets and changing PSFs. Do not call any excess scatter astrophysical variability without independent epochs and controls.

Independent archive check: for the eventual frozen tile coordinates query Gaia DR3 (astrometry/variability, G/BP/RP), plus DES/DECam or Pan-STARRS optical exposures **only if verified overlapping coverage**. Record survey, telescope, instrument, band, epoch and dataset IDs. Gaia is an independent telescope but not a direct VIS flux-calibration replicate; optical bandpass, resolution, depth and non-simultaneity limit comparisons. Multiple Euclid visits are *not* independent-telescope evidence. No specific external observations or identifiers have been retrieved, so independent matching is **not performed**.

Candidate policy: rank |standardized residual| among sources passing all flags, with multiple-testing-aware empirical null from matched control sources; retain a persistent ICRS/MER/PHZ/SPE candidate table only after valid source joins and image checks. No candidate coordinates or redshifts are inferred now. Planck18 applies if a subsequently verified extragalactic redshift motivates distance calculations, not to this instrumental repeatability statistic.

## Execution, reproducible blocker, and outputs
The repository includes `run-updates/deep_visit_repeatability_intake.py` which queries the official deep-mode TAP schemas and five preview rows, caps response bytes, logs errors, and does not generate fake measurements. At execution on 23 November 2026, direct IRSA TAP HTTPS access from the analysis environment failed DNS resolution (`NameResolutionError: Temporary failure in name resolution`). Consequently no live source rows, calibrated FITS, independent archive image IDs, observed cutout, candidate, statistical test, or scientific PDF can be supplied. This is an **access failure**, not a negative astronomical finding. The existing repository's verified observational results remain untouched.

Next: rerun intake in an IRSA-connected environment; freeze actual tile/columns; query finite visit rows and quality controls; independently verify external archive coverage; produce calibrated registered cutouts and a compact line-number-free PDF only after measurements.

## 365 Earthian Days — editorial draft (hold)
Day [number] out of 365 Earthian Days — How repeatable are Euclid's faintest galaxy measurements?

I am setting up a reproducible test of whether repeated Euclid near-infrared measurements show more scatter for faint sources than for brighter controls. It is a useful quality check before interpreting unusual colours or candidate variability.

The first live archive request could not resolve the data server, so I have no source-level result to report yet. The protocol separates instrumental repeatability from genuine astronomical variability and requires independent archive checks.

Notebooks, code and methods: https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation

You are welcome to write your own scripts, rerun the checks or suggest improvements.

#365EarthianDays #AstroNotebooks #OpenScience #Euclid
