**Author:** Biswajit Jana
**Date:** February 25, 2026

# Which TRAPPIST-1 planets are actually in the habitable zone?

I pulled the real system parameters for all seven TRAPPIST-1 planets from the NASA Exoplanet Archive: host-star effective temperature (2566 K), luminosity (0.00055 solar luminosities), and each planet's semi-major axis (average orbital distance).

I computed the habitable-zone (HZ) boundaries two ways: the simple inverse-square-law estimate (0.0224-0.0323 AU) and the Kopparapu et al. (2013) empirical fit using the star's actual temperature (0.0246-0.0499 AU). The two disagree by roughly 50% at the outer edge, which matters here -- and I flag honestly that TRAPPIST-1's 2566 K temperature is *below* the Kopparapu fit's calibrated range of 2600-7200 K, so that boundary is a modest extrapolation, not a fully validated number.

Placing the real planets against the Kopparapu boundaries: TRAPPIST-1 b, c, and d fall inside the inner edge (too hot), e and f fall within the computed habitable zone, and g and h fall outside the outer edge (too cold). Planet e sits only 0.0046 AU inside the inner boundary and f only 0.0114 AU inside -- both close calls, not comfortably centered in the zone.

The plot shows every planet's real position along the star-distance axis, shaded by both HZ estimates, with blue markers for planets that land inside the Kopparapu zone and red for those that don't.

**What I'd look at next:** rerun with the optimistic Kopparapu boundaries (Recent Venus/Early Mars) to see if d and g get included; propagate the semi-major-axis uncertainties into the classification since several planets sit close to a boundary; find an independent Teff measurement to check the extrapolation risk.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html. HZ formulation: Kopparapu et al. 2013, ApJ 765, 131.
