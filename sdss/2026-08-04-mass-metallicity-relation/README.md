**Author:** Biswajit Jana  
**Date:** June 18, 2026

# The stellar mass-gas metallicity relation from a real SDSS star-forming sample

More massive star-forming galaxies hold onto more of the heavy elements their stars produce -- deeper
potential wells retain metal-enriched gas against outflows, and more massive galaxies have converted more
of their gas into stars over cosmic time. This is the mass-metallicity relation (MZR), first characterized
at SDSS scale by Tremonti et al. (2004) for ~53,000 galaxies. I wanted to reproduce it from scratch on an
independent, live-queried sample rather than just cite the result: a single SQL query joins the base
`SpecObj` catalog with two real value-added catalogs -- `galSpecLine` (MPA-JHU emission-line fluxes) and
`galSpecExtra` (MPA-JHU stellar masses from full spectral+photometric fitting) -- for galaxies with S/N > 5
in H-alpha, H-beta, [O III], and [N II].

From that raw query I apply my own Kauffmann et al. (2003) BPT cut in Python (not the pipeline's label) to
isolate genuine star-forming spectra, then compute gas-phase oxygen abundance from scratch using the
Pettini & Pagel (2004) N2 calibration: `12+log(O/H) = 8.90 + 0.57 x log10([N II]/Ha)`. The final working
sample is 200 real star-forming galaxies (randomly capped from a larger selected pool, fixed seed for
reproducibility) spanning `log(M*/Msun)` from the low-mass dwarfs through massive spirals.

An ordinary-least-squares fit of metallicity against log stellar mass gives slope = 0.152 +/- 0.008 dex per
dex, Pearson r = 0.82 (r-squared = 0.67), p ~ 6e-50, and an RMS scatter of 0.059 dex around the best-fit
line -- a strong, highly significant positive correlation that reproduces the well-known qualitative shape
of the literature relation. The measured slope is somewhat steeper than Tremonti's canonical low-mass slope
because this sample is smaller and does not densely sample the highest-mass, flattening regime where the N2
calibration itself is known to saturate.

## What's next

Natural extensions: fit a quadratic term to test for the literature's reported high-mass turnover, compare
N2-based abundances against an independent strong-line calibration (O3N2 or R23) to quantify systematic
calibration uncertainty between indices, and add star-formation rate as a third axis to test the
fundamental metallicity relation (Mannucci et al. 2010), where metallicity depends jointly on mass and SFR.

## Data source and citation

- SDSS DR18 SkyServer SQL search: https://skyserver.sdss.org/dr18/
- MPA-JHU value-added catalogs (`galSpecLine`, `galSpecExtra`): https://wwwmpa.mpa-garching.mpg.de/SDSS/DR7/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- Tremonti et al. (2004), ApJ 613, 898: https://doi.org/10.1086/423264
- Kauffmann et al. (2003), MNRAS 346, 1055: https://doi.org/10.1111/j.1365-2966.2003.07154.x
- Pettini & Pagel (2004), MNRAS 348, L59: https://doi.org/10.1111/j.1365-2966.2004.07591.x
