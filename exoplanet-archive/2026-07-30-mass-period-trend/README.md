**Author:** Biswajit Jana
**Date:** May 6, 2026

# Do bigger planets orbit closer or farther? Mass vs. period

I pulled the full confirmed-planet mass/period table from the NASA Exoplanet Archive (6,333 raw rows), dropped 372 rows missing a mass or period, and kept the remaining 5,961 planets with positive values for both.

A log-log linear regression across all methods gives a slope of 0.550 +/- 0.013 (Pearson r = 0.494) -- but that combined number is misleading. Splitting by detection method tells a very different, and more honest, story: the transit sub-sample (4,651 planets) shows essentially **no** mass-period trend (slope -0.031 +/- 0.022, r = -0.020), while the radial-velocity sub-sample (1,195 planets) shows a strong positive trend (slope 0.693 +/- 0.020, r = 0.701).

That split is a real detection-bias signature, not noise: the median transit-detected planet is a small, close-in world (median period 8.0 days, median mass 0.022 Jupiter masses, i.e. roughly Neptune-scale), while the median RV-detected planet is a much more massive, farther-out planet (median period 308 days, median mass 1.10 Jupiter masses). Transit surveys are sensitive across a wide mass range at short period, which flattens any mass-period trend within that sub-sample; RV surveys are far more sensitive to massive planets, and their reach to longer periods grows with a planet's mass (more distant giant planets are still easier to detect via RV than nearby small ones), which produces the real positive slope in that sub-sample.

Two panels: a mass-vs-period scatter colored by detection method, and the same data in log-log space with the two fitted regression lines overlaid.

**What I'd look at next:** add microlensing/imaging as separate panels, weight the fit by reported mass uncertainty, and try a broken power law to capture the hot-Jupiter pileup visible in the transit sub-sample.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
