**Author:** Biswajit Jana  
**Date:** June 21, 2026

# Searching for the Hyades moving group (supercluster) in the field with real Gaia DR3 kinematics

The Hyades cluster has a known extended kinematic relative -- the "Hyades moving group" or
"supercluster" -- field stars scattered well beyond the cluster's tidal radius that still share its
space motion. I tried to find real evidence of it using only Gaia DR3 data. First I pulled a real
Hyades core sample (cone search plus a parallax cut and a proper-motion box around the cluster's
known bulk motion, pmra ~ +101, pmdec ~ -28 mas/yr) and kept only the 85 real members with a
measured radial velocity, giving a tight, realistic velocity dispersion (sigma_U = 2.75, sigma_V =
0.50, sigma_W = 1.23 km/s) -- a good sign the selection is genuinely picking out bound cluster
members rather than field contaminants.

I then pulled a real field sample (60-150 pc, full 6D data, more than 20 degrees from the cluster
centre so genuine members are excluded by construction) and computed each star's real Galactic
space velocity the same way. Searching for field stars within 5 km/s of the cluster's mean velocity
turned up 23 candidates out of 5,804 field stars (0.4%).

Comparing that against a null test (random field-star centres, same tolerance sphere) gave a mean
expected match count of 14.26 -- so the observed 23 is only a modest ~0.5-sigma excess, not a
strong detection. I think that's an honest result: this simple velocity-box method is a real but
blunt tool, and the null test itself is conservative (built from the real, disk-dominated field
distribution rather than an idealized isotropic one), so a clean stream signal needs either a
tighter clustering algorithm or a chemical-abundance cross-check to really stand out.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
