**Author:** Biswajit Jana
**Date:** February 21, 2026

# Do RV and transit discoveries have the same eccentricity distribution?

I compared orbital eccentricities across discovery methods using a quality-cut archive sample of 5,146 planets. A Kruskal-Wallis test across methods came back with p < 1e-300 -- the methods clearly do not share a common eccentricity distribution, and the sample is large enough that this isn't a fluke.

The split is stark: radial-velocity discoveries have the highest median eccentricity (0.155), while transit discoveries have the lowest (0.000). That matches the physical story -- RV surveys are more sensitive to longer-period giant planets that tidal forces haven't had time to circularize, while transit surveys are dominated by short-period planets that mostly have been tidally circularized already.

The plot compares eccentricity by discovery method directly, with the notebook's bootstrap and rank-based robustness checks confirming the difference isn't an artifact of a few outliers.

**What I'd look at next:** control for orbital period directly, since it's the main physical driver, to isolate any purely methodological bias from the "RV finds more long-period planets" effect.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
