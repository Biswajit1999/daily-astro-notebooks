# Recovering HAT-P-7b's orbital period from scratch with a periodogram

In the other light-curve notebooks in this folder I started from an already-known orbital period to fold the
data. Here I wanted to do it the other way around: pretend I didn't know HAT-P-7b's period at all, and try
to recover it purely from the shape of its real Kepler light curve using a Box Least Squares (BLS)
periodogram — an algorithm built specifically to search for the box-shaped dips transits produce.

I downloaded a Kepler light curve for the host star, ran a BLS search across a range of candidate periods,
and plotted the resulting periodogram to find the period with the strongest transit-like signal.

The periodogram's tallest peak landed right on top of HAT-P-7b's published orbital period (about 2.2 days),
and folding the light curve on that recovered value — not the value I already knew from the literature —
produced a clean transit dip. That matters because it shows the algorithm genuinely found the real signal on
its own, rather than the result being rigged by already knowing the answer.

This is essentially the same search technique real survey pipelines use to flag transit candidates out of
hundreds of thousands of light curves, and it was satisfying to see it actually work end to end on one real
target.

**What I'd look at next:** inject a fake, much fainter transit signal into a flat light curve with known
parameters and run the same search, to see how faint a signal this method can still recover before it gets
lost in noise.
