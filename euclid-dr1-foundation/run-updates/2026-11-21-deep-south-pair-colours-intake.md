# 2026-11-21 — Deep Field South compact-pair colour contamination: archive gate

Biswajit Jana · operations intake; **not an observed study, new numbered science day or discovery**.

## Repository and release audit
Read `RESEARCH_INDEX.md` on master (generated 10 August 2026; its indexed 100 notebooks do not establish the state of the November Euclid branch), and the Euclid research branch README and the 19–20 November run updates. Existing EDF North compact doubles, Fornax infrared outliers, ACT cluster colour, H-alpha and spectroscopy studies must not be recast as new findings.

Checked the ESA DR1-Foundation Explanatory Supplement (12 November 2026), IRSA data-products inventory (12 November), IRSA data-access guide (18 November), and the IRSA release notice (12 November). Scope: official release documentation and archive-access screen only; no successful ADS/arXiv completeness or target-specific literature search. No novelty assertion. References:
- https://euclid.esac.esa.int/dr/dr1/expsup/master.html
- https://irsa.ipac.caltech.edu/euclid-archive-documentation/data-products/
- https://irsa.ipac.caltech.edu/euclid-archive-documentation/data-access/
- https://irsa.ipac.caltech.edu/news.html

## Proposed independent falsifiable question (NOT EXECUTED)
**Title: Do close neighbours inflate apparent extreme VIS–NISP colours in a fixed Euclid Deep Field South cone?**

Preregistered finite sky footprint: ICRS RA=62.500 deg, Dec=-48.000 deg, radius=0.025 deg; this is a *candidate footprint*, not a claim of verified DR1 coverage. Source: DR1-Foundation deep-survey MER catalogue and its released VIS/Y/J/H images and quality/mask maps, after checking schema and units. Compare unique primary sources with neighbours within 1.5 arcsec against isolated sources beyond 3 arcsec, matched in VIS magnitude and NISP J S/N; exclude saturated, edge, masked, diffraction/persistence, nonpositive flux and ambiguous deblends. Freeze the exact published flags and magnitude/SNR limits only after fetching the official dictionary, before looking at outcome values. Define extreme colour as the upper 1% of VIS–J in the full quality-passing parent sample; report the threshold and its bootstrap uncertainty. Compare contamination fractions using stratified permutation and bootstrap 95% confidence intervals; reject apparent outliers whose colour depends on aperture choice or overlapping segmentation. A null is no significant difference after quality and brightness matching. Candidate table must contain ICRS, MER/PHZ/SPE IDs where present, flags, bands, neighbours, mask diagnostics, competing interpretations and FITS cutout links. Do not assign redshift or distance from a colour alone.

Independent archives to query after positions are verified: DECam/DECaLS or VISTA imaging as available, Gaia DR3 for stellar foreground and motions, and optical spectroscopy from DESI/other archives only when sky coverage and target matches are established. Record actual telescope/instrument/band/observation identifiers, depth and PSF differences. Euclid repeat bands are not independent telescopes. No coverage or independent matching is claimed here.

## Executed gate and reproducible blocker
Read-only IRSA TAP test from the analysis environment attempted the public TAP endpoint with a TOP 1 deep-survey MER query; it failed with a DNS NameResolutionError, before an HTTP response or any rows. This is a *runtime network-resolution blocker*, not an empty catalogue, zero candidates or a null result. The connected GitHub API was accessible. Added `run-updates/euclid_dr1_tap_probe.py` to capture schema and a one-row availability response, including response hashes, for an environment with archive access. Its outputs have not been run or verified against live IRSA from this runtime. The exact cone query must be generated only after confirming the actual coordinate column names via TAP_SCHEMA; do not assume a column name or silently change the footprint. No sample, observational analysis, calibrated image, registered comparison, PDF or science-day number is warranted.

Next gate: run the probe where IRSA resolves; verify catalogue schema, coordinate units and footprint membership; archive exact ADQL, response and SHA256; freeze cuts; extract a finite cone and genuine FITS images; cross-match independent archives; then compute and report results. Do not merge master.

## 365 Earthian Days — editorial hold, science day unassigned
Day [number] out of 365 Earthian Days — Can a nearby galaxy make another galaxy look unusually red?

I am preparing a small, falsifiable Euclid DR1-Foundation test of whether very close neighbours distort optical-to-infrared colours. The archive query was blocked by network name resolution before any sources could be inspected, so there is no measured result or unusual-object claim yet.

Code, notebook index and methods: https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation ; public data access: https://irsa.ipac.caltech.edu/euclid-archive-documentation/data-access/

You're welcome to write your own scripts, rerun the query or suggest stronger independent checks.

#365EarthianDays #AstroNotebooks #OpenScience #Euclid
