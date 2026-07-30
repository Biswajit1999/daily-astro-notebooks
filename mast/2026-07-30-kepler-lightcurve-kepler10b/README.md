# Seeing Kepler-10b's transit dips in a real Kepler light curve

Kepler-10b was one of Kepler's first confirmed rocky exoplanets — a small, blisteringly hot world orbiting
its star in under a day. A transit light curve just tracks a star's brightness over time, and when a planet
crosses in front of the star, brightness dips very slightly and briefly. I downloaded a real Kepler light
curve for this star with `lightkurve` and looked for those dips directly.

The raw light curve for a single Kepler quarter doesn't show anything obvious by eye — each individual
transit is far too small and brief relative to normal stellar brightness variation and instrument noise.
Folding the light curve on the planet's known 0.837-day orbital period stacks every one of the roughly 36
transits from that quarter on top of each other, and that's what turns an invisible signal into a small but
clear dip right at phase zero.

Seeing that stacking trick actually work on real data made concrete something I'd only read about before:
this is genuinely how such a tiny, rocky planet's transit gets detected in the first place — not from one
dramatic dip, but from combining many faint ones.

**What I'd look at next:** fit an actual transit model to the folded curve to measure the transit depth and
duration directly from this data, rather than relying on the already-published values.
