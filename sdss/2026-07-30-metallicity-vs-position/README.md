# Does stellar metallicity change with position in the galaxy?

I pulled about 400 SDSS stars that have measured stellar parameters from the SEGUE Stellar Parameter
Pipeline (the `sppParams` table) and checked whether their metallicity (how much of their mass is elements
heavier than hydrogen and helium — astronomers lump all of that together as "metals") correlates with
Galactic latitude.

The idea is that stars closer to the Galactic plane tend to have formed more recently, out of gas already
enriched by earlier generations of stars, so you'd expect some kind of metallicity trend with position.

I converted each star's RA/Dec into Galactic coordinates with `astropy`, plotted metallicity against
Galactic latitude, and computed a simple correlation coefficient between the two.

The correlation I found was weak. That's not too surprising once I thought about it: this SDSS
spectroscopic sample isn't a uniform grid across the sky — it follows the survey's specific targeting
choices, and different stars in the sample sit at very different distances from us, which confounds any
clean latitude trend. A fair test would need to control for distance first. Still, it was a useful exercise
in pulling stellar parameters via SQL and converting sky positions into a Galactic reference frame.
