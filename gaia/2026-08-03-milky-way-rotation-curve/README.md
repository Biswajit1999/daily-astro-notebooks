**Author:** Biswajit Jana  
**Date:** February 26, 2026

# A Milky Way rotation curve from real Gaia DR3 radial velocities

I pulled a real sample of 12,000 Gaia DR3 stars that have measured radial velocities (line-of-sight
velocity from Gaia's onboard spectrograph), good parallax signal-to-noise (>10), and clean astrometry
(RUWE < 1.4), spanning distances of roughly 0.3-6.7 kpc from the Sun. Using `astropy`, I converted
each star's sky position, parallax, proper motion, and radial velocity into a full 3D position and
velocity in a Galactocentric frame (Sun at 8.122 kpc from the Galactic centre), then worked out each
star's galactocentric radius and its rotational (azimuthal) velocity around the Galaxy.

After restricting to stars within 0.5 kpc of the Galactic plane and to galactocentric radii of 4-13
kpc (9,131 stars survived), I binned by radius and took the median rotational velocity in each bin.
The result is a genuinely flat rotation curve: it sits around 209-227 km/s pretty consistently from 4.75
kpc all the way out to 11.75 kpc, with the bin nearest the Sun's own radius (8.25 kpc) landing at 225.3
+/- 0.5 km/s. That's a nice match to the commonly cited "flat" Milky Way rotation velocity of about 220
km/s, and it's the same flatness (rather than the Keplerian decline you'd expect from the visible mass
alone) that's one of the classic pieces of evidence for dark matter in spiral galaxy discs.

The catch is that this is a radial-velocity-selected sample, not a volume-complete one: Gaia only has
spectroscopic radial velocities for stars bright enough for its onboard instrument, which biases things
toward more luminous stars and toward the inner, denser part of the sample volume. The outer bins (past
about 11-12 kpc) also have far fewer stars and noticeably larger scatter, so I'd treat the curve's
flatness way out there with more caution than the well-populated inner bins.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
