# Building a real Hertzsprung-Russell diagram for the Pleiades

I pulled real Gaia astrometry and photometry for stars in the direction of the Pleiades, cut the sample down
to likely cluster members using a parallax range around the cluster's known distance (about 136 parsecs),
and plotted an HR diagram: each star's color against its brightness.

An HR diagram is the single most useful plot in stellar astrophysics because a star's position on it
encodes its temperature, luminosity, mass, and rough evolutionary stage all at once. Building one from a
real, messy catalog query (rather than a textbook example) meant handling real photometric scatter and
figuring out my own membership cut from parallax.

The main sequence — the tight diagonal band running from hot and bright at one end to cool and faint at
the other — showed up clearly once I converted apparent brightness to absolute brightness using each star's
individual Gaia distance. Because the Pleiades is young (roughly 100 million years old), there's no
noticeable population of evolved giant stars yet — the most massive members haven't had time to burn
through their core hydrogen and move off the main sequence.

Doing this for a real cluster, with real Gaia photometric noise and a hand-picked parallax cut instead of a
pre-cleaned membership catalog, made the whole idea of an HR diagram feel a lot more concrete than it does
in a textbook diagram.
