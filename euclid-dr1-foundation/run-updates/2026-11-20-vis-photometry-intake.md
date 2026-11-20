# 2026-11-20 — VIS photometry calibration sensitivity: intake gate

Biswajit Jana · dated research operations update; **not a new science/publication day**

## Archive and literature check (20 November 2026)
Reviewed the existing master study index and editorial register and the research branch's Fornax colour-outlier study and 19 November spectroscopy intake. The official ESA DR1-Foundation Explanatory Supplement dated 12 November 2026, particularly section 15 and its VIS PSF/aperture photometry calibration figures, reports two photometric-code bugs and a validation example at tile 102159192. IRSA says catalogues are being added to its services incrementally. Checked the DR1 release overview (Euclid Collaboration, Aussel et al., arXiv:2611.16510) and IRSA MER mosaic and deep-visit dataset DOIs. This is a limited release-documentation and title/abstract screen, not an exhaustive ADS/arXiv novelty search. The calibration caveat is already publicly documented: it is **not** a new discovery.

Sources: https://euclid.esac.esa.int/dr/dr1/expsup/ ; https://arxiv.org/abs/2611.16510 ; https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html ; https://doi.org/10.26131/IRSA683 ; https://doi.org/10.26131/IRSA677

## Distinct proposed falsifiable question — NOT EXECUTED
**Title:** Are extreme VIS PSF-minus-aperture flux residuals in DR1-Foundation tile 102159192 associated with catalogue quality flags and magnitude?

Dataset/field: DR1-Foundation MER tile **102159192**, not the Fornax colour-outlier footprint or EDF North H-alpha sample. This tile ID is documented in the ESA calibration example, but its public MER table availability, column names, units and footprint have **not** been verified in this run.

Before reading science values, freeze the exact tile identifier and quality flags from the current MER dictionary. Query the full tile (finite footprint), require finite positive VIS PSF and aperture fluxes and their uncertainties, clear invalid/masked/deblend flags, and deduplicate primary MER IDs. Compare bright unsaturated and faint objects in prespecified magnitude bins, with a star-like control subset selected from documented morphology/flags; avoid interpreting all galaxies as PSFs. Compute residual delta = -2.5 log10(F_PSF/F_aperture), bootstrap medians and 95% confidence intervals by magnitude bin; predeclare a two-sided permutation test of bright-versus-faint medians. Inspect 10 largest residuals with actual VIS FITS cutouts, masks and neighbours; rank by |delta|/sigma and reject blends, saturation, edges and bad pixels. Quantify uncertainty covariance and PSF/aperture differences before attributing residuals to software calibration. The null is no detectable residual trend after these cuts; no claim about bug correction can follow from released data alone without paired reprocessed measurements.

Independent checks: query Gaia DR3 for astrometric/photometric star controls and Pan-STARRS1 or DECam/HSC imaging for footprint and source morphology, recording instrument, band, identifiers, match radius, depth and PSF differences. Gaia and ground optical filters are **not** direct replacements for Euclid VIS flux calibration; repeated Euclid flux estimators are not independent observations. Coverage queries and matching have not been performed.

## Actual gate / result
No verified tile-specific MER catalogue extract, source-level FITS cutouts, mask values or independent matched archive responses were obtained. Consequently no sample size, residual, significance, candidate table rows, observed target image, PDF or new science day can be reported. Do not interpret the documented release calibration figures as measurements performed here. This update records a reproducible data-intake blocker, not a tested null.

Next gate: retrieve MER table metadata and row count for tile 102159192 through ESA/IRSA; archive exact TAP ADQL and response checksum; verify VIS flux units and quality-bit meanings; freeze the sample and control thresholds; fetch VIS cutouts and independent archive coverage; then run conventional Python statistics and generate the observed-image report. Preserve the existing master and research branch and all existing study records.

## 365 Earthian Days — editorial draft (unassigned; do not post without review)
Day [number] out of 365 Earthian Days — Can a photometry calibration issue mimic an unusual galaxy?

Euclid's 12 November DR1-Foundation documentation describes photometric calibration issues and validation tests. I have prepared a separate, testable question: do VIS PSF-versus-aperture flux differences depend on brightness and catalogue quality in one documented tile? The source-level test is blocked until the exact catalogue and imaging inputs are verified, so there is no measured effect or discovery to report yet.

Notebook index, protocols and data access: https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation ; https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html

You are welcome to write scripts, rerun the checks or suggest stronger independent controls.

#365EarthianDays #AstroNotebooks #OpenScience #Euclid
