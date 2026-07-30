# How circular are exoplanet orbits, really?

Our own solar system's planets have nearly circular orbits (low eccentricity). I wanted to check whether
that's typical of planets elsewhere, using real measured orbital eccentricities for thousands of confirmed
exoplanets from the NASA Exoplanet Archive, and see whether planets on short vs. long orbits look different.

I histogrammed the eccentricity of the whole confirmed-planet sample, then split it into short-period
(under 10 days) and long-period (over 100 days) groups and compared their median eccentricities directly.

There's a big pileup of planets near zero eccentricity, but a long tail out to quite eccentric, elongated
orbits. Splitting by period showed something real and physical: short-period planets are systematically
much more circular than long-period ones. That's not a coincidence — strong tidal forces from the star
gradually circularize a close-in planet's orbit over time (the same effect that keeps our Moon's orbit
around Earth so circular), while planets further out don't feel that tidal pull as strongly and can retain
more eccentric orbits left over from however they originally formed.

It was satisfying to see a genuine physical mechanism (tidal circularization) show up as a clear, testable
pattern in real archival data rather than just reading about it.

**What I'd look at next:** look specifically at multi-planet systems, where eccentricities also get damped by
mutual gravitational interactions between planets, to try to separate that effect from tidal circularization.
