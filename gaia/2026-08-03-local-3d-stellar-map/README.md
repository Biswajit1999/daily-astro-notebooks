# Mapping the local stellar neighborhood in 3D with real Gaia DR3 parallaxes

I pulled a real sample of 6,000 bright (G < 10), nearby Gaia DR3 stars with parallax > 10
milliarcseconds (meaning distance < 100 pc) and good parallax signal-to-noise. Using `astropy`, I
converted each star's sky position and parallax-based distance into 3D Cartesian Galactic coordinates
(X, Y, Z in parsecs, Sun at the origin), then plotted both a face-on (X-Y) and edge-on (X-Z) projection
of where these stars actually sit around us.

I then counted stars in concentric 20 pc shells out to 100 pc and worked out a real number density
(stars per cubic parsec) in each shell: 143 stars in the innermost 0-20 pc shell (density 4.27e-3
stars/pc^3), climbing to 2,251 stars in the 80-100 pc shell but with a lower density of 1.10e-3
stars/pc^3 because the shell's volume grows so much faster than its star count. So the apparent density
drops by roughly a factor of 4 from the innermost to outermost shell in this sample.

That drop is not really telling us the Sun sits in a locally underdense patch of the Galaxy — it's a
selection effect. This is a magnitude-limited sample (G < 10), not a truly volume-limited one: at 20 pc
I can see every star down to a fairly faint intrinsic brightness, but by 100 pc only the intrinsically
brighter stars still make the G < 10 cut, so fainter, more common stars (especially M dwarfs) silently
drop out of the more distant shells. The real local stellar density, dominated by faint low-mass stars,
is considerably higher than what a bright sample like this can show.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
