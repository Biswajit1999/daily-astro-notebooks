**Author:** Biswajit Jana  
**Date:** July 8, 2026

# M13 (NGC 6205): globular cluster membership and HB/RGB identification from real Gaia DR3 data

I pulled a real Gaia DR3 sample of 6,000 sources (an unbiased random subsample, via Gaia's
`random_index` column, of the roughly 26,500 real sources within a 0.3 degree cone) around the
globular cluster M13. Because M13 sits at about 7 kpc, its parallax is only ~0.14 mas -- far too
small and noisy to use for membership, unlike the nearby open clusters in the other notebooks in
this folder. So membership here comes entirely from proper motion: I built a real vector-point
diagram, found the density peak of the field's proper-motion distribution, and selected stars
within 0.6 mas/yr of that peak (plus a BP/RP photometric-quality cut) as cluster members. That gave
2,092 members out of the 6,000-star subsample.

The resulting mean proper motion, pmra = -3.18 +/- 0.22, pmdec = -2.59 +/- 0.24 mas/yr, lines up
almost exactly with the literature Gaia-DR3-based value for M13 (Vasiliev & Baumgardt 2021: pmra =
-3.18, pmdec = -2.56 mas/yr) -- a good sanity check that the simple density-peak membership method
recovers the real cluster kinematics.

I then built a real colour-magnitude diagram from the member sample and identified two classic
globular-cluster CMD features: the horizontal branch (found at apparent G ~ 19.17, a near-constant-
luminosity band of core-helium-burning stars spanning a wide colour range -- 551 candidates) and
the red-giant branch (stars brighter than the HB level and redder than BP-RP = 0.7 -- 394
candidates).

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
