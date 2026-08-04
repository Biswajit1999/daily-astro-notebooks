**Author:** Biswajit Jana  
**Date:** February 4, 2026

# The 4000-Angstrom break as a real stellar-population age diagnostic

Old stellar populations pile up metal absorption right around 4000 Angstroms (rest frame), producing a real
step down in flux blueward of that wavelength -- the 4000-Angstrom break, D4000. Young, hot star-forming
populations have a much weaker break. I wanted to measure this directly from real SDSS spectra rather than
just quote the textbook prediction, so I pulled 4 real `STARFORMING`-classified galaxies and 4 real passive
galaxies (no strong emission-line subclass) and computed the narrow D4000 index (Balogh et al. 1999:
`Fnu(4000-4100 A) / Fnu(3850-3950 A)`, converting flux density to per-unit-frequency units first) from scratch
for each one.

The result cleanly separates the two groups exactly as predicted: the four star-forming galaxies give
D4000_n = 1.356, 1.443, 1.445, 1.489 (median 1.444), while the four passive galaxies give 2.031, 2.034, 2.047,
2.051 (median 2.040) -- a difference of 0.596 in the medians, with zero overlap between the two groups in this
small sample. The comparison plot makes the physical reason visible directly: the passive galaxies' spectra
show a real, sharp step down in flux across the 4000-A break, while the star-forming galaxies stay comparatively
flat.

What makes this a genuinely useful check rather than a circular one: I computed D4000 purely from each
spectrum's flux, with no reference at all to the SDSS pipeline's own `SUBCLASS` label. That my from-scratch,
textbook-formula measurement still lands on the same star-forming/passive split the pipeline already made is
real, independent evidence that the index measures what it's supposed to.

## What's next

I would scale this up from 4+4 galaxies to a real statistical sample of dozens to hundreds per class, add
BPT-composite galaxies to see if their D4000 falls between the two extremes as an age/star-formation-history
diagnostic predicts, and cross-check my values against the SDSS `galSpecIndx` value-added catalog's own D4000_n
measurements for the same objects.

## Data source and citation

- SDSS DR18 spectra: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- Balogh et al. (1999): https://doi.org/10.1086/307258
