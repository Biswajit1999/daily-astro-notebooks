# Measuring an H-alpha emission line in a star-forming galaxy

I took a real SDSS galaxy spectrum and measured the width and strength of its H-alpha emission line — the
brightest visible-light signature of hot young stars ionizing hydrogen gas around them.

After shifting the spectrum into the galaxy's own rest frame using its measured redshift, I fit a Gaussian
curve (plus a straight line for the underlying continuum) to the H-alpha feature to pull out its center and
width. Converting that wavelength width into a velocity using the Doppler relation gives a rough measure of
how turbulent or fast-rotating the gas is inside the galaxy.

The velocity width I measured came out in the range typical for an ordinary star-forming galaxy disk —
nothing dramatic, no signs of unusually violent gas motion. That's actually a useful negative result: it
tells me this looks like a normal galaxy rather than one caught in a merger or hosting an unusually active
nucleus.

The most interesting part for me was just watching a Gaussian fit converge cleanly on real, noisy
astronomical data — it's a good reminder that a lot of astrophysics measurement comes down to fitting
simple curves to real spectra and trusting the fit parameters, as long as you sanity-check them against
known physical ranges.
