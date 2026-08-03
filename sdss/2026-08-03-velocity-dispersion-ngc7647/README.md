# NGC 7647: measuring stellar velocity dispersion from absorption line widths

SDSS's own pipeline reports NGC 7647's stellar velocity dispersion as 268.4 +/- 4.7 km/s, from a full
spectral-template fit. I wanted to try measuring it myself, more simply: fit a Gaussian to a single real
absorption feature, correct for instrumental blurring using SDSS's actual per-pixel `wdisp` array (not an
assumed constant resolution), and see what I get.

I fit Ca II K (3934.777 A rest) and the Mg b blend (~5175 A rest) separately as single Gaussian absorption
dips against a locally linear continuum. Converting the fitted widths to velocities and subtracting the real
instrumental dispersion in quadrature gave sigma = 610.2 km/s from Ca II K and 564.0 km/s from Mg b -- both
more than double the pipeline's 268.4 km/s.

That is a real, honest discrepancy, and I think it says more about the limits of my method than about the
galaxy. SDSS's pipeline fits the whole usable spectral range against a library of stellar templates
simultaneously (the same spirit as the widely-used pPXF method), so the continuum and the line broadening are
solved for jointly. My method fits one isolated feature against a naive straight-line local continuum, which
breaks down here in two specific ways: Ca II K sits right at the edge of the 4000-Angstrom break, where the
true continuum curves quickly, so a linear local fit biases the measured width high; and Mg b is not one line
but a blend of three close transitions (roughly 5167, 5173, 5184 A) plus weaker iron lines, so a single
Gaussian conflates real velocity broadening with the intrinsic separation between the blended components.

The real lesson here is a methodological one: instrumental-resolution correction using the real `wdisp` array
is necessary but not sufficient for an accurate velocity dispersion -- line blending and continuum placement
matter just as much, and that is exactly why professional pipelines avoid single isolated-line Gaussian widths
in favor of full-spectrum template fitting.

## What's next

I would fit the Mg b blend as three separate Gaussians instead of one to remove the blending bias, try a
genuinely isolated line without a nearby steep continuum break to see if that converges closer to the pipeline
value, and implement a simplified pPXF-style approach that convolves a stellar template with a trial Gaussian
kernel and fits by chi-squared over the whole window rather than fitting the raw data with a Gaussian profile.

## Data source and citation

- SDSS DR18 spectra: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- Cappellari (2017), pPXF full spectrum fitting: https://doi.org/10.1093/mnras/stw3020
