# How far away is Vega, really? Measuring it from Gaia parallax

Parallax is the tiny yearly back-and-forth wobble a nearby star appears to make against the distant
background sky as Earth orbits the Sun — the bigger the wobble, the closer the star. It's the most direct,
purely geometric way we have to measure a star's distance. I looked up Vega, one of the brightest stars in
the northern sky, in the real Gaia catalog and worked out its distance from its measured parallax myself.

I resolved Vega's coordinates by name, queried Gaia for sources at that position, and pulled the brightest
match's parallax and parallax uncertainty, then converted parallax in milliarcseconds directly into a
distance in parsecs and light-years using the standard 1000/parallax relation.

My distance estimate came out at almost exactly 25 light-years, matching the commonly quoted figure. What I
found genuinely striking is that this whole result rests on measuring one extremely small angle against the
sky — Gaia's entire multi-billion-star catalog is fundamentally built out of exactly this kind of
measurement, done with a precision that would have seemed impossible before the mission.

It's a small notebook, but it's a clean illustration of how something as basic-sounding as "how far away is
that star" ultimately comes down to a single well-measured angle.
