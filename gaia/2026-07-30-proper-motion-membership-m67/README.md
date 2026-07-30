# Finding cluster members of M67 using proper motion alone

Proper motion is how fast a star appears to creep across the sky each year. Stars gravitationally bound
together in a cluster share almost the same proper motion because they're moving through the galaxy as a
group, while foreground and background stars that just happen to be in the same direction have essentially
random motions. I wanted to see if I could pick M67 cluster members out of a field of thousands of Gaia
stars using proper motion alone, no parallax or radial velocity needed.

I queried all Gaia sources in a half-degree radius around M67, plotted every star's proper motion in RA
against its proper motion in Dec, and then applied a simple distance cut around the cluster's known motion
to flag candidate members.

The result was a satisfying, obvious clump of stars sharing nearly identical motion, sitting clearly apart
from the much more scattered field population. Visualizing "before" (all stars) and "after" (candidate
members highlighted) side by side made the separation really easy to see.

What struck me is how much this reveals with such a simple method — no spectra, no distance measurements,
just two numbers per star (proper motion in two directions) are enough to isolate a real physical group from
thousands of unrelated interlopers.
