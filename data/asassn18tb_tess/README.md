# ASASSN-18tb / SN 2018fhw time-domain data

This directory freezes two 15x15-pixel TESSCut target-pixel files from MAST
(Sectors 1 and 2), the public MIT TESS Transients cleaned light curve, and
DES DR2 g/r/i HiPS cutouts served by CDS. The transient coordinates are
RA 64.526108 deg, Dec -63.615069 deg (ICRS).

TESS pixels are about 21 arcsec wide, so the host galaxy and neighbouring
sources are blended. The notebooks use difference images or baseline-subtracted
flux and do not interpret the raw aperture sum as isolated supernova light.
The MIT file is an automatically processed difference-light-curve product; its
background model and the known scattered-Earthlight intervals are treated as
systematic checks. DES images predate the explosion and describe the host field,
not the supernova at maximum light.

Primary context: Vallely et al. (2019, MNRAS 487, 2372) report a single-power-law
rise index 1.69 +/- 0.04, first light MJD 58341.68 +/- 0.16, B-band maximum
MJD 58357.33 +/- 0.12, and strong late H-alpha emission. The notebooks attempt
an independent compact remeasurement but do not claim a new progenitor result.
