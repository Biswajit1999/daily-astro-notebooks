# NGC 7647: a quiescent elliptical, for contrast with the AGN notebook

This is the deliberate opposite case to my NGC 5875 notebook: I ran the exact same automated line-ID pipeline
(median-filter continuum, S/N-thresholded `scipy.signal.find_peaks`, de-redshift, cross-match against a
literature line list) on a genuinely different galaxy type and wanted to see how the results changed.

NGC 7647 (SDSS plate 6136, MJD 56206, fiber 728, RA 350.989, Dec 16.777) is a passive galaxy at z = 0.041077
+/- 9.9e-6, with SDSS's own pipeline reporting a large stellar velocity dispersion of 268.4 +/- 4.7 km/s --
a genuinely massive elliptical -- and a high median spectral S/N of 47.3.

The peak finder turned up 30 candidate features: 8 marginal "emission" bumps (median S/N only 6.1, right at
the edge of my 5-sigma threshold) clustered in the noisier blue end of the spectrum, and 22 real absorption
features. Cross-matching against the same literature line list and 6-Angstrom tolerance used for NGC 5875,
9 of the 30 detections matched cleanly -- fewer than in the emission-line galaxy, and I think that is mostly
because this galaxy's much larger velocity dispersion (268 km/s vs. NGC 5875's narrower lines) physically
broadens and shifts the apparent centroids of absorption features like Ca II H&K, the G-band, and the Mg b
blend beyond a fixed narrow tolerance.

I'm treating the 8 low-significance emission bumps as noise, not real detections: they sit right at the
threshold, don't correspond cleanly to any strong nebular line at this redshift, and are exactly what I'd
expect from a genuinely quiescent galaxy with no ongoing star formation or active nucleus to power real
emission lines. That contrast -- unambiguous, high-S/N, well-matched emission lines in NGC 5875 vs. marginal,
unmatched noise bumps here -- is itself a meaningful result about what these two galaxies are.

## What's next

I would measure the actual velocity dispersion directly from these absorption line widths (see my companion
`2026-08-03-velocity-dispersion-ngc7647` notebook), fit a real stellar population template to separate weak
genuine emission from continuum-fitting noise, and check whether the marginal blue-end bumps are reproducible
across repeat SDSS observations of the same object.

## Data source and citation

- SDSS DR18 spectra and images: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- NIST Atomic Spectra Database: https://physics.nist.gov/PhysRefData/ASD/lines_form.html
