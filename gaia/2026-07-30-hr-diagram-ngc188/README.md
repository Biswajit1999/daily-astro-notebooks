**Author:** Biswajit Jana  
**Date:** March 5, 2026

# NGC 188: an HR diagram for one of the oldest nearby open clusters, and its real turnoff

NGC 188 is roughly 6-7 billion years old, far older than the Hyades or Pleiades I looked at in
the sibling notebooks in this folder, and it's also much farther away (~1.8-1.9 kpc vs tens of
parsecs), so this notebook uses a relaxed parallax S/N cut (>3) and leans more on a
proper-motion box for membership. Starting from 3356 raw Gaia DR3 sources in a 0.4 degree field,
the full cut sequence (parallax S/N, RUWE < 1.4, BP/RP quality, a parallax window around the
cluster's distance, and the proper-motion box) left 1087 candidate members with a median
distance of 1902 pc (16th-84th percentile: 1739-2091 pc).

Because NGC 188 is genuinely old, its main-sequence ridge line shows a real bend rather than
just running out at the bluest sampled star — I located it numerically as the point where the
ridge stops getting brighter moving from red to blue, landing at color ~ 2.12, M_G ~ 7.22. I
then overlaid all three clusters' ridge lines (Pleiades, Hyades, NGC 188) on one comparison
plot, and the ranking comes out exactly as expected from their known ages: the Pleiades turnoff
sits bluest/brightest, the Hyades in between, and NGC 188 reddest/faintest — a genuine,
quantitative demonstration of using main-sequence turnoff position as a relative-age indicator
across three real clusters.

## What I'd look at next

Replace the "monotonic ridge bend" turnoff finder with a real isochrone fit for a quantitative
age in Gyr, and correct for differential reddening across the field, which matters more here
than for the much closer Hyades/Pleiades.

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
