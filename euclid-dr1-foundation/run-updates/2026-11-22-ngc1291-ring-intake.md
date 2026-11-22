# 2026-11-22 — NGC 1291 outer-ring colour asymmetry: preregistration and data gate

Biswajit Jana · **not an observational result; science day unassigned**

## Prior-work and archive audit
Read the current master Euclid study index and branch directories, including the 19–21 November intake records and the existing ACT cluster colour result. This is a **different named galaxy** from the NGC 4236 UV-knot study, EDF North spectroscopy, ACT fields, and Deep South pair-colour intake. The ESA DR1-Foundation release and explanatory supplement are dated 12 November 2026. ESA's release image explicitly identifies NGC 1291 (ICRS nominal centre RA 03:15:30, Dec −41:42:34). Release documentation, ESA's NGC 1291 image caption, IRSA overview, and the published Euclid Q1 lens literature were screened; **no exhaustive ADS target-specific paper search was completed**, so no novelty assertion is justified.

Sources: https://euclid.esac.esa.int/dr/dr1/expsup/ ; https://euclid.caltech.edu/page/euclid-dr1-foundation ; https://euclid-ec.net/ ; https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html ; https://arxiv.org/abs/2611.16510

## Distinct, narrow falsifiable question
**Is the outer ring of NGC 1291 measurably more azimuthally asymmetric in Euclid VIS than in independent GALEX NUV imaging, after matching resolution and masks?**

Preregistered finite footprint: 0.15 degree radius centred at ICRS (48.875000 deg, −41.709444 deg), **conditional on confirmed released DR1-F image coverage and WCS**. This is a search footprint, not a measured ring boundary. Input: calibrated DR1-F Euclid VIS FITS image, weight and mask maps; GALEX GR6/7 NUV intensity/exposure maps as a genuinely independent telescope comparison, provided archive coverage and image IDs can be verified. Additional independent optical DECam/DES imaging only if an overlapping released exposure is confirmed. Repeat Euclid exposures do not count as independent evidence.

**Freeze before measuring:** confirm FITS provenance, photometric units, zero point, astrometry, masks, effective PSF, Galactic extinction, and the ring's inner/outer ellipse on the VIS image; record the ellipse parameters and sky-annulus choice before evaluating azimuthal contrast. Convolve VIS to the GALEX NUV effective PSF, reproject to a shared WCS, use the same ring ellipse and valid common-coverage mask. Divide the ring into 12 equal-position-angle sectors, estimate background-subtracted mean surface brightness with robust sigma-clipped background and uncertainties propagated from weight/exposure maps. Normalize each band's sector fluxes by its positive ring-integrated flux; compare the dimensionless asymmetry statistic A=(P90−P10)/median of sector intensities. Bootstrap by spatially coherent image blocks (not individual pixels), report 95% intervals for A_VIS, A_NUV, and their difference. Null criterion: the difference interval contains zero. Do not infer a stellar age gradient or star-formation contrast without extinction and population modelling; VIS and NUV probe different populations and have different sensitivity to dust.

Quality and rejection gates: astrometric offset, background gradients, bright-star masks, diffraction wings, saturated pixels, mosaicking seams, incomplete ring coverage, correlated pixels, PSF mismatch, and foreground Gaia DR3 stars. If GALEX coverage is incomplete or too shallow, record a non-comparison rather than interpreting absence of NUV flux. No redshift or cosmological distance is necessary for this angular, normalized comparison; Planck18 would apply only if a separately justified redshift-derived quantity is introduced.

## Actual execution and blocker
The verified inputs in this run are **release descriptions and the existing repository records**, not calibrated NGC 1291 FITS arrays. No DR1-F VIS FITS image, mask, calibrated GALEX NUV FITS or GALEX dataset identifier was retrieved, and no target-specific ADS coverage or independent image comparison was completed. Therefore the preregistered statistic cannot be calculated and no observed cutout, candidate table row, statistical significance, PDF or publication day is asserted. The ESA processed press image is evidence of a public target image, **not** a substitute for calibrated surface photometry.

Next execution: locate released Euclid VIS product identifier and GALEX GR6/7 tile IDs, retrieve FITS and checksums, validate WCS/units/PSFs, freeze the ring ellipse and quality cuts, then run the sector comparison and export registered observed cutouts and a compact PDF. Candidate table should remain empty until measured object-level candidates exist. Preserve all nulls and unsuccessful coverage checks.

## 365 Earthian Days — editorial hold
Day [number] out of 365 Earthian Days — Does NGC 1291's outer ring look different in ultraviolet and visible light?

Euclid's November release includes an image of the ring galaxy NGC 1291. I'm preparing a reproducible comparison of the ring's brightness around its circumference, using Euclid visible-light imaging and independent GALEX ultraviolet observations.

The calibrated images and their masks have not yet been verified together, so I cannot report a measured asymmetry or physical interpretation. This is a preregistered question, not a discovery claim.

Research protocol and code index: https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation ; data documentation: https://euclid.esac.esa.int/dr/dr1/expsup/

You're welcome to write your own scripts, reproduce the archive checks or suggest improvements.

#365EarthianDays #AstroNotebooks #OpenScience #Euclid
