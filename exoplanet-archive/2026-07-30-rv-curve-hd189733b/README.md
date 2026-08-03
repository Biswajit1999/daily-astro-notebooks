# Reconstructing HD 189733 b's radial-velocity wobble

HD 189733 b is a well-studied hot Jupiter around a nearby K dwarf. I pulled its real fitted orbital solution from the NASA Exoplanet Archive: period P = 2.2186 days, eccentricity e = 0.0 (fixed circular in the archive's adopted fit), argument of periastron omega = 20 deg, RV semi-amplitude K = 205.0 m/s, and host-star mass 0.79 solar masses.

I built the actual Keplerian RV curve from those real parameters by solving Kepler's equation for the eccentric anomaly and converting to true anomaly at each phase. With e = 0 the curve reduces to an exact sinusoid, phase-shifted by omega.

As an internal-consistency check, I inverted the binary mass function to compute the minimum mass Msini directly from K, P, e, and stellar mass: Msini = 1.125 Jupiter masses. Using the archive's reported orbital inclination (85.71 deg, since this is a transiting system the inclination is well constrained), the implied true mass is 1.129 Jupiter masses -- within 0.1% of the archive's own reported mass (1.130 Jupiter masses), a strong internal-consistency check given the transiting geometry pins the inclination tightly.

No genuine time-series RV data points were reachable in this sandbox, so the plot shows the model curve only -- stated honestly rather than inventing residual scatter.

**What I'd look at next:** since HD 189733 b transits, cross-check the RV-based Msini against the transit-derived true mass more rigorously by also pulling the transit-fit inclination uncertainty; look for public archival RV time series (e.g. from HARPS discovery-paper tables) to overplot real data points.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
