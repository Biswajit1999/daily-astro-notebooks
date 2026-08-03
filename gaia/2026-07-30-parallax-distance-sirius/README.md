# Measuring the distance to Sirius, the brightest star in our sky

Same approach as the Vega notebook: I queried Gaia DR3 around Sirius's coordinates first, and
again every returned source is fainter than G=8, while Sirius's true apparent magnitude is
V=-1.46 — far too bright for Gaia's routine pipeline. So I used the Hipparcos catalog (van
Leeuwen 2007 re-reduction) instead, queried live via VizieR.

Hipparcos gives Sirius (HIP 32349) a parallax of 379.21 +/- 1.58 mas, which converts to a
distance of 2.637 +/- 0.011 pc (8.60 light-years) — a 0.11% difference from the commonly cited
2.64 pc literature value. Sirius is famous for its large proper motion, and I confirmed that
directly: total proper motion of 1339.41 mas/yr, which combined with the Hipparcos distance
gives a tangential velocity of 16.74 +/- 0.07 km/s (sky-plane component only; the full 3D space
velocity would also need Sirius's radial velocity).

## What I'd look at next

Add Sirius's radial velocity to get its full 3D space velocity, and compare this Hipparcos
parallax against earlier ground-based parallax measurements to see how much precision improved
between eras of astrometry.

**Citation:** Hipparcos (van Leeuwen 2007, `I/311/hip2`) via VizieR/CDS; Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
