# Measuring the distance to Sirius, the brightest star in our sky

Sirius is the brightest star we see at night, mostly because it happens to be genuinely close to us, not
because it's unusually luminous. I pulled its real Gaia astrometric solution and worked out its distance
from parallax, then also looked at its proper motion — Sirius is well known among nearby stars for moving
comparatively fast across the sky.

After resolving Sirius's coordinates and querying Gaia around that position, I converted its parallax into a
distance and combined its proper motion with that distance to estimate its actual sideways (tangential)
velocity through space, in kilometers per second.

The distance came out at roughly 8.6 light-years, matching the well known figure, and the tangential
velocity worked out to a few tens of kilometers per second — fast enough that Sirius's position against the
background stars measurably shifts over just a few thousand years.

One thing worth flagging: Gaia's astrometry can be less reliable for extremely bright stars like Sirius
because they can saturate the spacecraft's detectors, so a careful analysis would cross-check this parallax
against the older Hipparcos mission's independent measurement rather than taking Gaia's number alone at face
value.
