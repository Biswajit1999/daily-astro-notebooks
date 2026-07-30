# Can you tell quasars from galaxies just by their colors?

Before anyone takes a spectrum of anything, SDSS's photometric survey has already measured every object's
brightness through five broad filters (u, g, r, i, z — running from ultraviolet to near-infrared). I wanted
to check whether a simple color-color plot, using just two of those filters, actually separates quasars
from ordinary galaxies.

Quasars tend to look bluer than typical galaxies at the same overall brightness, because a lot of their
light comes from a hot accretion disk around a supermassive black hole rather than from starlight. I pulled
about 1,500 real objects with SDSS photometry that also have a spectroscopically confirmed class (quasar or
galaxy), and plotted u-g color against g-r color for each group.

The two populations really do separate reasonably well on this plot — quasars cluster toward bluer u-g
colors while galaxies spread out toward redder colors — though there's real overlap in the middle where
you'd need a spectrum to be sure.

This is exactly why surveys like SDSS use color cuts as a cheap first pass to pick out likely quasar
candidates before spending expensive telescope time on spectroscopy. It was neat to reproduce, with real
data, the basic logic behind a technique that's used across essentially the whole field.
