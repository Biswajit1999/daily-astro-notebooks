**Author:** Biswajit Jana  
**Date:** February 18, 2026

# How far away is Vega, really? Measuring it from a real parallax

I first tried Gaia DR3 directly, querying a small cone around Vega's coordinates. It's a useful
negative result: every source returned is fainter than G=9, while Vega's true apparent magnitude
is V=0.03 — Vega saturates Gaia's detectors and simply doesn't have a usable direct astrometric
solution in `gaia_source`. Rather than pretend one of those faint background sources is Vega, I
fell back to the Hipparcos catalog (van Leeuwen 2007 re-reduction), which was purpose-built for
bright naked-eye stars like this one, and queried it live via VizieR.

Hipparcos gives Vega (HIP 91262) a parallax of 130.23 +/- 0.36 mas, which converts to a distance
of 7.679 +/- 0.021 pc (25.04 light-years). That's a 0.02% difference from the commonly cited
literature distance of 7.68 pc — about as close an agreement as you can get. I also computed
Vega's tangential velocity from its real proper motion (349.72 mas/yr total) and this distance:
4.74 * mu[arcsec/yr] * d[pc] gives 12.73 +/- 0.04 km/s across the sky plane (the true 3D space
velocity would also need Vega's radial velocity, which isn't in this notebook).

## What I'd look at next

Add Vega's radial velocity to get a full 3D space velocity, and check whether Gaia's dedicated
bright-star or non-single-star reprocessing (outside the main `gaia_source` table) has a usable
solution where the routine pipeline doesn't.

**Citation:** Hipparcos (van Leeuwen 2007, `I/311/hip2`) via VizieR/CDS; Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
