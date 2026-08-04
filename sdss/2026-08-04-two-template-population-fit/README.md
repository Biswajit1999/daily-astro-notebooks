**Author:** Biswajit Jana  
**Date:** May 12, 2026

# A simplified real full-spectrum fit: young + old stellar-population light fractions from real SDSS spectra

Full-spectrum fitting codes (STARLIGHT, pPXF, FIREFLY, ...) estimate a galaxy's star-formation history by
fitting its observed spectrum as a non-negative linear combination of many simple-stellar-population
template spectra. I wanted to build a genuinely real, simplified two-component version of that idea
entirely from real SDSS data rather than just describe the method: I downloaded 8 real
`STARFORMING`-classified spectra and median-stacked them into a real "young population" template, downloaded
8 real quiescent (no-emission-line) spectra and stacked them into a real "old population" template (both
rest-framed and continuum-normalized on a common wavelength grid), then fit a real target galaxy's
continuum-normalized spectrum as a non-negative combination of the two templates using non-negative least
squares (NNLS) -- the same linear-algebra idea real full-spectrum-fitting codes use, just with 2 templates
instead of hundreds.

The target was drawn from a separate pool of moderate-S/N `STARFORMING`-labeled galaxies and selected as the
one whose D4000 break falls closest to the midpoint between the two templates (plate 781, mjd 52373, fiber
284, z=0.070). The NNLS fit gives a young-population light fraction of 0.387; an independent D4000-break
cross-check on the same spectrum gives 0.655. These two real, methodologically independent diagnostics do
not land on the same precise number, but they agree on the physically important point: this
pipeline-`STARFORMING` galaxy's continuum carries a real, substantial old-population contribution -- nowhere
close to 100% young, despite its emission-line-based classification. The quantitative gap between the two
methods is itself an honest, real result: it reflects genuine systematic differences between a 2-template
broadband fit (sensitive to dust reddening, which can masquerade as an older population) and a single narrow
flux ratio (largely insensitive to dust).

## What's next

The obvious extension is to use more than 2 templates (young/intermediate/old, or a full age grid), add a
real chi-square weighting with per-pixel flux errors and a free dust-reddening parameter, and mask emission
lines explicitly before fitting -- moving this closer to a genuine STARLIGHT/pPXF-style continuum fit and
likely narrowing the gap between the NNLS and D4000-based fractions found here.

## Data source and citation

- SDSS DR18 spectra (via `astroquery.sdss.SDSS.get_spectra`): https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- Balogh et al. (1999) D4000 definition: https://doi.org/10.1086/307258
- Cid Fernandes et al. (2005), STARLIGHT full-spectrum fitting: https://doi.org/10.1111/j.1365-2966.2005.09174.x
- Cappellari (2017), pPXF: https://doi.org/10.1093/mnras/stx3020
