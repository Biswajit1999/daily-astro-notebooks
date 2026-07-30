# Does a bigger planet really block more starlight?

When a planet passes in front of its star (a transit), it blocks a small fraction of the star's light — the
transit depth. Simple geometry says a bigger planet should block roughly its own cross-sectional area's
worth of light, so I pulled real transit depth and radius measurements for thousands of confirmed planets
from the NASA Exoplanet Archive to check whether that relationship actually holds up.

I plotted transit depth against planet radius on a log-log scale and fit a straight line through the cloud
of points to get a power-law slope, then compared that to what simple geometry predicts (a slope near 2,
since transit depth scales with radius squared).

The fitted slope came out close to that geometric prediction, which was reassuring, but there's real scatter
around the trend line. That scatter isn't noise in the usual sense — it's mostly because the host stars in
this sample vary a lot in size, and transit depth depends on the *ratio* of planet radius to star radius, not
planet radius alone. A small planet around a small star can produce the same depth as a big planet around a
big star.

This was a good reminder that a "clean" physical relationship in real archival data often needs one more
normalization step (dividing by host star size, in this case) before it actually tightens up the way the
underlying physics predicts.
