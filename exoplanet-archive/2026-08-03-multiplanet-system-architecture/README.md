**Author:** Biswajit Jana
**Date:** June 8, 2026

# Which multi-planet system is really a resonance chain?

I pulled real orbital periods and semi-major axes for three well-known multi-planet systems straight from the NASA Exoplanet Archive: TRAPPIST-1 (7 planets), Kepler-90 (8 planets, archived under its Kepler Object of Interest name `KOI-351`), and HD 219134 (6 planets). For every pair of neighbouring planets I computed the ratio of their orbital periods and found the closest simple fraction (like 3:2 or 5:3, denominator capped at 4), then measured how far off the real ratio is from that simple fraction as a percentage.

The result: TRAPPIST-1 sits closest to a genuine low-integer resonance chain, with a mean deviation of only 1.21% across its six period-ratio pairs -- consistent with published dynamical studies that describe it as a librating seven-planet chain. HD 219134 comes in second at 1.52%, but that number is a bit misleading: its planets aren't really in a resonance chain, it just happens that two of its five period ratios land close to 2:1 by coincidence, sitting alongside one enormous ~24x period gap between its five close-in planets and its one distant giant. Kepler-90 has the loosest fit of the three, with a mean deviation of 2.02% (rising to 3.04% under a stricter test using only denominators up to 3) -- its planets are tightly packed but not particularly resonant.

A robustness check repeating the same matching with a stricter denominator cap (3 instead of 4) leaves the ranking unchanged, which is reassuring but doesn't prove real dynamical resonance locking -- that would need transit-timing-variation data and N-body modelling, which this notebook doesn't attempt.

The plot shows each system's orbital spacing by planet index alongside each pair's deviation from its nearest low-integer resonance.

**What I'd look at next:** pull actual transit-timing-variation measurements for Kepler-90 and HD 219134 to test for real libration, since near-integer period ratios can occur by chance in tightly packed systems that aren't dynamically locked.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
