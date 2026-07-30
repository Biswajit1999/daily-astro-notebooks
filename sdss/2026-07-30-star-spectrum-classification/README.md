# Classifying a single SDSS star spectrum

I pulled down one real stellar spectrum from SDSS (a star at RA 0h8m05.6s, Dec +14d50m23s) and looked at
whether I could tell what kind of star it is just by eyeballing the spectrum shape, before checking my
guess against SDSS's own automated classification.

A spectrum is basically brightness measured across many narrow wavelength (color) bins. Different stars
show dips (absorption lines) at specific wavelengths depending on their surface temperature and chemical
makeup, and that pattern is what astronomers use to sort stars into spectral types.

I grabbed the spectrum with `astroquery.sdss`, plotted the full flux curve, and then read off the
pipeline's own `CLASS` and `SUBCLASS` fields to see what SDSS had already decided about this object. One
thing worth flagging: `astroquery.sdss` currently talks to SDSS DR17's data servers, not DR20, even though
the survey has moved on since then — the star's spectrum itself is the same real data either way, it's
just the software endpoint that's a few data releases behind.

Nothing shocking turned up here — the spectrum looked like an ordinary main-sequence star, and the pipeline
classification matched what I expected from the shape. The main value of this notebook for me was building
a clean, reusable pattern for grabbing and plotting any single SDSS spectrum, which I'll reuse for the
quasar and white dwarf notebooks in this same folder.
