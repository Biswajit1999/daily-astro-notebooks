# The Hyades cluster: an HR diagram for the nearest open cluster to us

I ran the same real Gaia DR3 pipeline here as in the Pleiades notebook, this time on a 3.0
degree field around the Hyades. Out of 168 raw sources, a parallax S/N > 5 cut, RUWE < 1.4,
BP/RP photometric quality cuts, a parallax window around the cluster's ~47 pc distance, and a
proper-motion box around its bulk motion left 87 candidate members. Their median distance came
out to 46.6 pc (16th-84th percentile: 45.2-49.1 pc), matching the literature value well.

I built the same kind of absolute-magnitude HR diagram and empirical main-sequence ridge line
as for the Pleiades, then did the actual comparison the two notebooks were designed for:
overlaying both ridge lines on one plot. The Hyades' turnoff proxy sits at color ~ 0.37, M_G ~
2.12 — clearly redder and fainter than the Pleiades' turnoff (color ~ -0.02, M_G ~ 0.78). That's
exactly the direction you'd expect: the Hyades, at roughly 700 million years old, is several
times older than the ~100 million year old Pleiades, so its more massive main-sequence stars
have already had time to evolve away, pulling the observed turnoff down and to the red. It's a
nice, checkable example of using relative turnoff position as an age indicator without needing
an absolute age calibration.

## What I'd look at next

Fit a real isochrone to the ridge line to convert this qualitative comparison into an actual age
in Myr, and replace the fixed proper-motion box with a proper iterative sigma-clip like the one
I used in the M67 notebook.

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
