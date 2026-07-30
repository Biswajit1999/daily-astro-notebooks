# A slice through the galaxy redshift survey -- SDSS's own "cone diagram"

I wanted to make my own small version of one of cosmology's most iconic plots: the "cone diagram," where
you take a thin wedge of sky and plot every galaxy in it by redshift (a stand-in for distance) and sky
position, and the large-scale structure of the universe shows up as clumps and gaps.

I pulled about 3,000 real SDSS galaxies from a narrow declination strip (-1.25 to +1.25 degrees) out to
redshift 0.3, and plotted them on a polar plot with angle as sky position and radius as redshift.

Even in this fairly narrow slice, the galaxies clearly aren't spread evenly — they gather into denser
strands with darker, near-empty gaps between them. That clumpy, web-like pattern is the "cosmic web," the
large-scale structure that gravity has pulled ordinary and dark matter into over billions of years, and
seeing it fall out of a simple SQL query and a scatter plot on real survey data was genuinely satisfying.

What struck me most is how little effort it took to reveal this — no fancy statistics, just plotting
position and redshift for a few thousand real galaxies is enough to see the structure by eye. It's a good
reminder of why large redshift surveys were such a big deal for cosmology in the first place.
