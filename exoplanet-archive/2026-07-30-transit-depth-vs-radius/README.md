# Does a bigger planet really block more starlight?

I pulled the current confirmed transiting-planet sample from the NASA Exoplanet Archive's `pscomppars` table via a live TAP query (4,716 raw rows), then applied real quality cuts: requiring a finite planet radius, host-star radius, and reported transit depth (dropped 217 rows), plus a physical sanity range on radii (dropped 1 more). That leaves a clean sample of 4,498 transiting planets.

For each planet I computed the simple geometric transit-depth prediction, depth = (Rp/Rstar)^2, from the archive's own radius columns, and compared it to the archive's separately reported/derived transit depth (`pl_trandep`). The two agree reasonably well but not perfectly: the log10(reported/geometric) residual has an RMS of 0.135 dex and a robust median absolute deviation of 0.059 dex, with reported depths running about 10% higher than the pure-geometry prediction on average (median ratio 1.096). That gap is consistent with real effects the pure-geometry formula ignores -- limb darkening, non-zero impact parameter, and the fact that `pl_trandep` and `pl_rade`/`st_rad` aren't always fit from the same light curve.

I then split the sample into physically meaningful radius classes -- sub-Earth, Earth-sized, super-Earth/sub-Neptune, Neptune-sized, and Jupiter-sized -- and printed the count and log-log depth-radius slope in each bin. The bins show real, uneven sample sizes (for example, far more super-Earth/sub-Neptune planets than sub-Earth ones), reflecting detection biases in the underlying surveys rather than the true population.

Two plots: a geometric-vs-reported depth comparison with a 1:1 line and a residual histogram, and a size-class-colored depth-vs-radius scatter plot with per-bin counts in the legend.

**What I'd look at next:** restrict to planets whose stellar radius comes from the same paper as the depth measurement, add limb-darkening/impact-parameter corrections, and compare RV-confirmed vs. transit-only sub-samples.

**Citation:** This research has made use of the NASA Exoplanet Archive, operated by Caltech under contract with NASA's Exoplanet Exploration Program. https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html
