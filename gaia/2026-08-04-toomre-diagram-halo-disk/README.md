**Author:** Biswajit Jana  
**Date:** January 2, 2026

# Halo vs. thick-disk vs. thin-disk kinematic separation with a real Gaia DR3 Toomre diagram

I pulled a real Gaia DR3 sample of stars within 50 pc of the Sun (parallax > 20 mas) with good
parallax signal-to-noise, good astrometric fit quality (RUWE < 1.4), and -- critically -- a real
measured radial velocity, so I had full 6D phase-space information for every star. That cut
returned about 19,700 real sources; I took an unbiased 8,000-star random subsample (via Gaia's
`random_index` column) to keep the analysis tractable while preserving the true population mix.

For each star I computed a real Galactic space velocity (U, V, W) relative to the Local Standard of
Rest, using `astropy.coordinates` to transform each star's real (ra, dec, parallax, pmra, pmdec,
radial_velocity) into Galactic Cartesian velocity components, then correcting for the Sun's own
motion relative to the LSR. I built a real Toomre diagram (total U-W speed vs. rotation velocity V)
and applied standard total-LSR-speed thresholds to classify each star.

The results looked like a realistic local stellar-population mix: 61.8% thin disk (v < 50 km/s),
16.65% thick disk (70-180 km/s), a 21% thin/thick transition zone, and just 0.54% (43 stars) in the
halo regime (v >= 180 km/s). That's exactly the expected shape for a 50 pc bubble around the Sun --
thin-disk stars dominate locally, and halo stars are intrinsically rare in the solar neighbourhood,
so a small but non-zero halo tail is the right real-data outcome.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
