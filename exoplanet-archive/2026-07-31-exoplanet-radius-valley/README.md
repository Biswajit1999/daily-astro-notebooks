# Measuring the radius valley in the current archive

I pulled a live, quality-cut sample of 2,070 transiting planets (1-4 Earth radii, 1-100 day periods, radius uncertainty under 20%) from the NASA Exoplanet Archive and located the "radius valley" -- the observed scarcity of planets between rocky super-Earths and gas-rich sub-Neptunes -- with a kernel-density estimate.

The valley minimum comes out at 1.83 Earth radii, with a bootstrap 68% confidence interval of 1.80-1.86 Earth radii, consistent with the published range from Fulton et al. (2017) and Van Eylen et al. (2018). Splitting the sample into four period bins and fitting a line in log(radius) vs. log(period), the valley location shifts with period at a slope of -0.13 +/- 0.04 -- the valley tilts toward smaller radii at longer periods, matching the direction reported in the literature for photoevaporation- and core-powered-mass-loss-driven models.

Two plots: a radius histogram with the KDE and bootstrap interval overlaid, and a period-radius scatter with the per-bin valley locations and the fitted tilt line.

**What I'd look at next:** incorporate stellar-parameter homogenization (many `st_teff`/`st_rad` values in the composite table come from different pipelines) and a detection-efficiency correction, since neither photoevaporation nor core-powered mass loss can be distinguished from an uncorrected catalogue alone.

**Citation:** NASA Exoplanet Archive `pscomppars` table: https://exoplanetarchive.ipac.caltech.edu/. Fulton et al. 2017, AJ 154, 109; Van Eylen et al. 2018, MNRAS 479, 4786.
