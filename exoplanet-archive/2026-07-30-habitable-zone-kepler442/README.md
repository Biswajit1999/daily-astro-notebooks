**Author:** Biswajit Jana
**Date:** August 3, 2026

# Is Kepler-442 b actually in the habitable zone?

I pulled the real Kepler-442 system parameters from the NASA Exoplanet Archive: host-star Teff (4402 K, within the Kopparapu et al. 2013 fit's valid 2600-7200 K range), luminosity (0.117 solar luminosities), and the one confirmed planet's semi-major axis (0.409 AU).

I computed the habitable-zone boundaries two ways: the simple inverse-square-law estimate (0.326-0.470 AU) and the Kopparapu (2013) empirical fit using the star's real temperature (0.347-0.646 AU). Kepler-442 b's real orbital distance, 0.409 AU, falls inside both computed zones -- under the more careful Kopparapu boundary it sits 0.0615 AU inside the inner edge, i.e. comfortably away from either boundary rather than a marginal case.

The plot places the planet's real position against both HZ estimates on a single distance-from-star axis, with the wider (weaker) inverse-square band and the narrower, temperature-corrected Kopparapu band shown together so the difference between the two methods is visible directly.

**What I'd look at next:** propagate the reported semi-major-axis uncertainty (+/-0.209 AU, which is large relative to the planet's distance) into the inside/outside call -- at the 1-sigma level the planet's true position is not tightly pinned down; rerun with optimistic HZ boundaries; and check for an updated orbital solution now that Kepler-442 b has had additional years of follow-up since discovery.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html. HZ formulation: Kopparapu et al. 2013, ApJ 765, 131.
