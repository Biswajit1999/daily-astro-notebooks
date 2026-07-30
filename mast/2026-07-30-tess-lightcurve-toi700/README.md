# TOI-700 d: hunting for an Earth-sized habitable-zone planet's transit in real TESS data

TOI-700 d was one of the first Earth-sized planets TESS found sitting in its star's habitable zone. I
downloaded a real TESS light curve for the host star and tried to spot its transit — a genuinely subtle
signal, since this planet is small and its star is faint, making this a good test of how much signal
processing real exoplanet detection actually takes.

After cleaning the light curve and folding it on the planet's published orbital period (about 37.4 days), the
unbinned data points alone didn't show much of anything by eye — the transit is small relative to the noise
in any individual TESS measurement. Binning the folded light curve, averaging groups of nearby points
together, is what brought out a faint dip near phase zero.

That was the most useful thing I took from this notebook: small, Earth-sized habitable-zone planets aren't
confirmed from one dramatic dip the way some hot Jupiters are. They come out of statistically stacking and
binning many faint, individually invisible transits — a much more patient process than the light curves you
usually see reproduced in articles about famous exoplanets.

**What I'd look at next:** combine light curves from the system's other available TESS sectors to build up
more transits and get an even cleaner binned signal.
