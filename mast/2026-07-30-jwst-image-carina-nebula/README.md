# Pulling a real JWST image of the Carina Nebula from MAST

The Carina Nebula is a huge star-forming region, and one of JWST's very first published images was a
close-up of its "Cosmic Cliffs" — a wall of gas and dust being sculpted by radiation from young, massive
stars. Instead of just looking at the famous press photo, I queried MAST (the archive that hosts JWST,
Hubble, Kepler, and TESS data) directly for real NIRCam observations of the region and pulled down an actual
calibrated preview image with a script.

I searched by coordinates rather than by name (target names in the archive don't always match common
names), found the NIRCam imaging observations near the nebula, pulled the product list for one observation,
and grabbed the calibrated mosaic ("i2d") preview rather than a raw or partially processed frame.

The image is a genuine calibrated product built directly from real NIRCam exposures — not the specific
press-release frame, but real data from the same survey region, retrieved straight from the archive rather
than downloaded by hand from a webpage. It's a good template for pulling any JWST imaging target this way.

**What I'd look at next:** download the actual FITS mosaic instead of just the preview JPEG and build my own
color composite from multiple filters, similar to how the official Cosmic Cliffs image was assembled.
