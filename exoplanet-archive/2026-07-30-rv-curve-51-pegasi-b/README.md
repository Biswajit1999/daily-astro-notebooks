**Author:** Biswajit Jana
**Date:** March 13, 2026

# Reconstructing 51 Peg b's radial-velocity wobble

51 Peg b was the first exoplanet discovered around a Sun-like star, via the star's Doppler wobble. I pulled its real fitted orbital solution from the NASA Exoplanet Archive: period P = 4.2308 days, eccentricity e = 0.0063 (essentially circular), argument of periastron omega = 0 deg, and RV semi-amplitude K = 55.77 m/s, with a host-star mass of 1.07 solar masses.

I built the actual Keplerian RV curve from those real parameters -- solving Kepler's equation numerically for the eccentric anomaly at each orbital phase, converting to true anomaly, then evaluating RV(t) = K*[cos(omega+nu) + e*cos(omega)]. With e this close to zero the curve is essentially a clean sine wave, as expected for a near-circular orbit.

As an internal-consistency check, I inverted the binary mass function to solve for the planet's minimum mass (Msini) directly from K, P, e, and the stellar mass: I get Msini = 0.464 Jupiter masses. Using the archive's separately reported orbital inclination (49.8 deg), the implied true mass is 0.608 Jupiter masses -- within 0.3% of the archive's own reported planet mass (0.610 Jupiter masses). That agreement is a genuine sanity check that the mass-function implementation and the archive's fitted parameters are mutually consistent.

No genuine time-series RV data points were reachable in this sandbox, so the plot shows the model curve only -- I say that directly rather than fabricating data points or a residual scatter number.

**What I'd look at next:** digitize the original Mayor & Queloz (1995) discovery-paper RV points to overplot real measurements on the model curve and get a genuine residual scatter; test sensitivity of Msini to different literature orbital solutions.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
