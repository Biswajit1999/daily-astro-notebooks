**Author:** Biswajit Jana
**Date:** May 16, 2026

# Do Kepler-9 and TRAPPIST-1 really deviate from a strict linear transit ephemeris?

I pulled every independently-published transit-midpoint and period solution for Kepler-9 (b, c, and a non-TTV control planet d) and all seven TRAPPIST-1 planets from the NASA Exoplanet Archive's Planetary Systems (`ps`) table -- 38 usable comparisons across 10 planets after cleaning. Unlike the composite `pscomppars` table, `ps` keeps one row per published parameter set, so a well-studied planet has several independently-fitted `(T0, P)` ephemerides logged over time. For each planet I anchored a strict linear ephemeris to its earliest published `(T0, P)`, extrapolated it forward, and computed observed-minus-calculated (O-C) residuals for every later published transit time.

Kepler-9 b and c -- both flagged `ttv_flag=1` by the archive -- show enormous O-C residuals: up to 766.5 minutes for b and 1141.9 minutes for c, hundreds of sigma in terms of the quoted timing uncertainties. Kepler-9 d, the same system's `ttv_flag=0` control planet, stays within 14.0 minutes (about 4.6 sigma). Kepler-9 b's median |O-C| is 33.6x the control's and c's is 23.1x -- a clean, large separation between the flagged-TTV planets and the non-TTV control in the same system, run through an identical pipeline. TRAPPIST-1's seven-planet resonant chain shows smaller but still real O-C residuals, up to 91.6 minutes across published solutions.

This recovers, rather than freshly discovers, a well-known result: Kepler-9 b and c are textbook TTV planets, first confirmed via their mutual perturbations near a 2:1 mean-motion resonance (Holman et al. 2010), and TRAPPIST-1's TTVs are the basis for its published planet masses (Agol et al. 2021; Grimm et al. 2018). The method here is deliberately coarse: the archive does not store epoch-by-epoch observed transit times in this table, only publication-level best-fit `(T0, P)` solutions, so each O-C point mixes real orbital motion with some amount of methodological scatter between independent fits. That caveat is stated explicitly in the notebook, and the ttv_flag=0 control is carried through the same pipeline specifically to check that the method isn't just manufacturing spurious "deviations" out of any noisy data -- it isn't, since the control stays an order of magnitude smaller.

The plot shows O-C diagrams (with propagated timing uncertainties) for Kepler-9's three planets and for all seven TRAPPIST-1 planets, each point representing one later publication's ephemeris checked against the earliest one.

**What I'd look at next:** pull the actual epoch-by-epoch transit-timing catalogs (e.g. the Kepler DR25 TTV catalog, or the individually-fitted transit times behind Agol et al. 2021 for TRAPPIST-1) instead of publication-level solutions, which would let me fit the real periodic TTV signal shape rather than just detect that a deviation from linearity exists.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
