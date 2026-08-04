**Author:** Biswajit Jana  
**Date:** June 2, 2026

# Looking for wide binary star pairs near Alpha Centauri

I looked up real Hipparcos astrometry for Alpha Centauri A and B (parallax ~755-797 mas, so I
used the system mean of 775.86 mas as the reference distance, plus mean proper motion pmRA =
-3646.82 mas/yr, pmDec = 638.33 mas/yr) and then searched Gaia DR3 in a 5 degree cone around the
system for anything with parallax > 200 mas (i.e. within about 5 pc, wide enough to include
Proxima Centauri's real 2.2 degree separation). Alpha Cen A and B themselves are too bright for
Gaia's routine pipeline, same saturation issue as Vega and Sirius in the other notebooks in this
folder, so they don't show up here — I only get whatever fainter, real companions might be in
the field.

The search returned exactly one candidate: a source 2.21 degrees away with G=8.98. I applied two
explicit numeric cuts to decide whether it's a real companion or a chance alignment: parallax
consistency (|Δparallax| < 50 mas from the Alpha Cen system value) and proper-motion similarity
(|Δμ| < 100 mas/yr, since Alpha Cen's own motion is huge at ~4000 mas/yr and a bound companion
should track it closely). That candidate has Δparallax = -7.8 mas (passes) but Δμ = 188.15
mas/yr (fails) — so 0 of 1 candidates in this search pass both cuts. It's moving too differently
through the galaxy to be gravitationally bound to Alpha Cen, despite being at a broadly similar
distance and appearing near the system on the sky.

## What I'd look at next

Widen the search to Proxima Centauri's exact position and check its known Gaia DR3 solution
directly (it's faint/red enough that Gaia does measure it, unlike A and B), and add a
physical-separation cut in AU once a candidate passes the parallax+PM test.

**Citation:** Hipparcos (van Leeuwen 2007, `I/311/hip2`) via VizieR/CDS; Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
