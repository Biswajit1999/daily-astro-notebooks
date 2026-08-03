# How fast is each detection method finding new planets?

I pulled real discovery-year and detection-method data for 5,786 confirmed exoplanets from the NASA Exoplanet Archive (2005-2025, the three leading methods only: transit, radial velocity, and microlensing) and built a cumulative discovery count per method per year. Then I fit a log-linear regression to each method's cumulative curve and converted the fitted slope into a compound annual growth rate (CAGR) -- a standard "how fast is this growing per year, on average" number.

Transit is growing fastest at a fitted 39.62%/yr (n=4,487 planets, fit r=0.930), radial velocity is the slowest of the three at 15.93%/yr (n=1,037, r=0.943), and microlensing sits in between at 27.42%/yr but with the tightest fit of all three (n=262, r=0.992). Transit's high growth rate is substantially driven by the Kepler mission's 2014 and 2016 data-release bursts plus ongoing TESS discoveries, rather than a single smooth improvement in detection capability. Radial velocity, being the oldest and most mature of the three methods, shows the steadiest but slowest growth.

A robustness check refitting the same three curves starting from 2012 instead of 2005 (to check whether the Kepler burst years were driving everything) kept the same ranking across methods, though the transit CAGR estimate is somewhat sensitive to exactly which years are included.

The plot shows cumulative discovery counts on a log scale by method, plus a bar chart comparing total 2005-2025 yield against fitted CAGR for each method.

**What I'd look at next:** break the transit method down by mission (Kepler vs. K2 vs. TESS vs. ground-based surveys), since lumping them together hides the fact that the transit growth curve is really a sum of several very different survey step-functions rather than one smooth process.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
