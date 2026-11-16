**Author:** Biswajit Jana  
**Date:** February 25, 2026

# Does the SDSS fiber-aperture upgrade actually show up in spectral S/N?

Legacy SDSS-I/II spectroscopy used 3-arcsecond-diameter fibers; BOSS and eBOSS switched to smaller,
2-arcsecond fibers. My starting prediction was simple physics: a smaller fiber should lose more light from an
extended galaxy for the same exposure, so at fixed apparent magnitude the legacy 3-inch fibers should reach
higher spectral S/N. I pulled a real sample of 4000 SDSS galaxy spectra (16 < Petrosian r-mag < 17.8, zWarning
= 0) via a live SQL query and checked this directly instead of just asserting it.

The sample split badly by era: only 73 of the 4000 spectra land in the BOSS/eBOSS (plate >= 3000, 2-arcsec
fiber) era, versus 3927 in the legacy (plate < 3000, 3-arcsec fiber) era, for this particular magnitude and
class cut -- an honest limitation of this specific selection, not something I smoothed over.

The actual result reversed my prediction. Binning both samples in 0.3-mag steps and comparing medians, BOSS/
eBOSS spectra show *higher* median S/N than legacy spectra at every magnitude where both eras have data --
the mean legacy/BOSS ratio across bins came out to 0.67, meaning legacy spectra typically reach only about
two-thirds of BOSS/eBOSS's median S/N at the same magnitude. My aperture-only prediction doesn't survive
contact with the real data. The most likely reason: BOSS/eBOSS used an upgraded spectrograph with better
CCDs and throughput, and its exposure-time strategy was tuned to reach a fixed high S/N per target (important
for its cosmological redshift work), actively compensating for the smaller fiber. That instrument-and-exposure
effect appears to dominate over, and reverse the sign of, the pure aperture effect I expected.

## What's next

I would pull a magnitude-matched, size-balanced random sample from each era rather than a raw top-N query,
bring in real per-plate exposure times if I can find them in the plate metadata tables to separate the pure
aperture effect from the exposure-time effect, and restrict to a narrower, better-matched redshift and galaxy
angular-size range, since fiber light loss depends on a source's size on the sky, not just its magnitude.

## Data source and citation

- SDSS DR18 SkyServer SQL search: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
