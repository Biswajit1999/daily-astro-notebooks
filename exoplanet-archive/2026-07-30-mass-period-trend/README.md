# Is there a real relationship between planet mass and orbital period?

I pulled thousands of confirmed exoplanets at once from the NASA Exoplanet Archive and looked for a
relationship between planet mass and orbital period, coloring each point by which method found it (radial
velocity or transit), expecting to see some kind of clean trend.

What I found instead was more interesting: no single power-law relationship, but distinct clusters that
trace back almost entirely to how each detection method works. Radial velocity surveys are naturally biased
toward finding massive planets, because a bigger planet causes a bigger stellar wobble to detect. Transit
surveys pick up a much wider range of masses, but are strongly biased toward short orbital periods, since a
planet has to transit repeatedly, in a reasonable observing window, to get confirmed.

So what looks at first glance like a "trend" in the raw combined data is really mostly a fingerprint of
detection bias rather than a fact about how planets actually form and settle into orbits. That was a useful
lesson for me: with survey data, you often have to understand the selection effects of how the data was
collected before you can say anything meaningful about the underlying population.

**What I'd look at next:** split the sample by detection method first, then look for a genuine mass-period
relationship within each method separately, since mixing them together mostly just shows the surveys'
different blind spots.
