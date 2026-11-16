# Carousel Lens pilot protocol

## Question

Can aperture colours from Euclid DR1-Foundation distinguish the near-redshift pair 1a and 2a in the Carousel Lens more clearly than the genuine counterimages 1a and 1b? Sheu et al. (2024) independently identified 2a as a different galaxy with spatially resolved MUSE spectroscopy. The classifications and aperture positions come from the literature before inspecting Euclid images. This is an image-plane test on one lens.

## Primary measurement

Use the O'Donnell et al. (2026) Table 2 fixed image centres. Measure H/Y and H/J flux ratios in identically placed circular apertures across Euclid VIS and NISP mosaics. Express the contrasts as differences of instrumental colours, so a global per-band zeropoint cancels. The primary colour is Y minus H and the secondary checks are J minus H and VIS minus H. Use a nominal 0.8 arcsec aperture and a local linear background estimated with robust clipping in a 1.25–2.25 arcsec annulus, excluding pixels near other listed arcs. Use matching 0.65 and 1.0 arcsec apertures and an alternative 1.5–2.5 arcsec annulus to check sensitivity. Repeat at a common nominal 0.85 arcsec effective FWHM to assess PSF sensitivity. If per-band stellar FWHM cannot be estimated, use a clearly stated approximate band PSF and label the homogenisation approximate. Inspect Euclid flag maps and local residuals. Same-source comparisons for sources 3 and 4 supplement the primary 1a/1b control, where reliable fluxes exist.

Estimate local random errors from aperture sums at nearby translated positions using the same algorithm and require flux in each band above 3 times its empirical local scatter. Report colour only where coverage is adequate and the denominator and numerator are significant by that rule. Background and aperture alternatives are systematic checks. Report failures and show observed cutouts even if colour comparisons remain inconclusive. A single larger contrast cannot establish a general separation rule, and lensing of different source regions, galaxy light, and PSF differences can change aperture colours.
