**Author:** Biswajit Jana  
**Date:** February 10, 2026

# Building a real Hertzsprung-Russell diagram for the Pleiades

I queried Gaia DR3 directly for a 1.0 degree field around the Pleiades and worked through a
real quality-cut pipeline instead of just plotting whatever came back. Starting from 855 raw
sources, I applied a parallax signal-to-noise cut (>5), a RUWE cut (<1.4, which flags stars
whose single-star astrometric fit is poor, often unresolved binaries), a BP/RP photometric
signal-to-noise cut, and a parallax window around the cluster's known ~136 pc distance. That
left 400 candidate members.

For each of those I computed a real absolute magnitude from its Gaia parallax (`M_G = G +
5*log10(parallax/1000) + 5`), not just its raw apparent brightness, and built the HR diagram
from that. The median member distance came out to 135.9 pc, with a 16th-84th percentile range
of 133.2-138.8 pc — consistent with the literature value. I fit a simple empirical
main-sequence ridge line (median absolute magnitude in color bins) and used it to locate a
turnoff proxy at color ~ -0.02, M_G ~ 0.78. Since the Pleiades is only about 100 million years
old, there's no real turnoff gap yet — essentially every mass sampled here is still burning
hydrogen on the main sequence, which is itself a useful, checkable statement I verify directly
in the companion Hyades and NGC 188 notebooks by overlaying all three ridge lines on one plot.

## What I'd look at next

Fit a real isochrone instead of an empirical ridge line to get a quantitative age, and
cross-check my simple parallax-window membership cut against a published Gaia DR3 Pleiades
membership catalog for false-positive/negative rates.

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
