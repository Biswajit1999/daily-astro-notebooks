# Does host-star metallicity predict giant-planet occurrence?

I pulled real host-star metallicity ([Fe/H], the iron-to-hydrogen ratio relative to the Sun) and planet mass for 815 unique radial-velocity-detected planet hosts from the NASA Exoplanet Archive, keeping each host's most massive known planet to avoid double-counting multi-planet systems. I flagged each host as a "giant host" if its most massive planet is at least 0.3 Jupiter masses (roughly Saturn-mass and above), then tested whether that flag correlates with metallicity.

The result: a positive, statistically significant point-biserial correlation of r = 0.103 (p = 0.0031) between having a giant planet and host-star metallicity. Splitting hosts into metallicity terciles makes the pattern concrete: 71.9% of metal-poor hosts, 71.2% of mid-metallicity hosts, and 85.9% of metal-rich hosts have a giant planet -- the effect is really concentrated in the metal-rich third of the sample rather than a smooth trend across all three bins. This is directionally consistent with the well-known giant-planet/metallicity correlation from RV surveys (Fischer & Valenti 2005), though the correlation here is numerically weaker than in dedicated occurrence-rate studies, likely because this sample only has detections (not the full list of stars searched) and mixes many different RV surveys with different target-selection ranges.

A robustness check using a stricter giant-planet threshold (1.0 Jupiter masses instead of 0.3) kept the correlation positive and significant (r = 0.096, p = 0.0063), with the same tercile pattern (metal-rich hosts at 72.2% giant fraction vs. ~58% for the other two terciles).

The plot shows the giant-host fraction by metallicity tercile alongside a scatter of the giant-host flag against [Fe/H] directly.

**What I'd look at next:** reconstruct actual per-survey target lists (not just detections) for at least one RV survey with public non-detections, since a true occurrence-rate estimate needs the denominator of stars searched, not just the detected planets -- this notebook only has the numerator.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
