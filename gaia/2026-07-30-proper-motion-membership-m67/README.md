**Author:** Biswajit Jana  
**Date:** April 16, 2026

# Finding M67 cluster members with a real proper-motion cut

I queried Gaia DR3 for a 0.6 degree field around M67, getting 2826 sources with valid parallax
and proper motion. Rather than eyeballing the dense blob in the proper-motion vector-point
diagram, I ran an iterative sigma-clip: start from a rough box around the cluster's known bulk
motion, compute the mean and spread inside it, shrink to 3-sigma, and repeat until it converges.
It converged in six iterations to 997 candidate members — about 35% of the field — with a
cluster mean proper motion of pmRA = -10.964 +/- 0.049 mas/yr, pmDec = -2.911 +/- 0.037 mas/yr,
and an intrinsic dispersion of about 0.20 mas/yr in each component.

To validate the cut, I split the field into the 997 selected members and the remaining field
stars and plotted both groups' color-magnitude diagrams side by side. The field stars scatter
broadly with no obvious structure, while the proper-motion-selected members trace out a clean,
narrow main sequence — exactly what you'd expect if the numeric cut is actually isolating a
real, coherent stellar population and not just a magnitude-limited subsample. The median
distance of the selected members came out to 868 pc, right in the middle of the commonly cited
850-900 pc range for M67.

## What I'd look at next

Add a parallax-consistency cut on top of the proper-motion cut to remove any remaining field
stars that happen to share the cluster's motion by coincidence, and compare the measured
dispersion to the expected dispersion from each star's individual `pmra_error`/`pmdec_error` to
see how much of it is real intrinsic cluster velocity spread versus measurement noise.

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
