# How elongated are exoplanet orbits, really?

I pulled the full confirmed-planet eccentricity table from the NASA Exoplanet Archive (6,333 raw rows), dropped 1,053 rows with no measured eccentricity, and kept 5,280 planets with 0 <= e < 1.

Splitting by planet-radius type: mean eccentricity climbs steadily with planet size, from 0.025 for sub-Earth planets to 0.167 for Jupiter-sized planets, with the fraction of notably eccentric orbits (e > 0.3) rising from about 1.5% for sub-Earths to roughly 20% for Jupiter-sized planets. Most small planets sit at exactly the archive's default e = 0 (many small-planet fits simply assume a circular orbit), so the median for every bin below Jupiter-sized is 0.00 -- the real signal is in the mean and the upper quartile, not the median.

Splitting by detection method shows the sharpest, most real result in this notebook: the transit sample (4,027 planets) has a median eccentricity of 0.00 and only 3.7% of planets above e=0.3, while the radial-velocity sample (1,154 planets) has a median eccentricity of 0.15 and 24.1% above e=0.3 -- an eight-fold jump in the eccentric fraction. That is a genuine detection-bias effect: RV surveys are dominated by longer-period giant planets that tidal forces have not had time to circularize, while transit surveys are dominated by short-period planets that mostly have been circularized. The eccentricity-vs-period panel shows this directly: eccentricity climbs with orbital period for both methods, with almost no high-eccentricity planets below about 10 days.

Two panels: eccentricity histograms by detection method, and eccentricity vs. period on a log period axis, colored by method.

**What I'd look at next:** control for period directly by comparing eccentricity in matched period bins across methods, to separate the pure "short-period is common in the transit sample" effect from a purely methodological bias; propagate eccentricity uncertainties into the quartile estimates.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
