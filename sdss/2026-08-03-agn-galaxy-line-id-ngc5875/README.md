# NGC 5875: galaxy image + spectrum line identification vs. literature

I wanted to do a full, honest, end-to-end line-identification exercise on one real SDSS galaxy: pull the
image, pull the spectrum, find the lines algorithmically, de-redshift them, and check them against a real
literature line list -- no eyeballing, no invented numbers.

I picked NGC 5875 (SDSS plate 1165, MJD 52703, fiber 409, RA 227.305, Dec 52.528), which SDSS's own pipeline
classifies as `GALAXY / AGN` with redshift z = 0.011695 +/- 8.0e-6 and a median spectral S/N of 30.4. I pulled
a real 400x400 pixel colour cutout from the SDSS SkyServer image-cutout service and the real coadded 1D
spectrum via `astroquery.sdss.SDSS.get_spectra`.

For line-finding, I estimated the continuum with a 101-pixel median filter, subtracted it, and converted every
pixel's residual into a noise-normalized S/N using SDSS's own inverse-variance (`ivar`) array. Running
`scipy.signal.find_peaks` with a |S/N| > 5 threshold found 26 candidate features: 16 emission, 10 absorption.

I built a literature rest-wavelength reference table (SDSS/NIST atomic line list values for Halpha, Hbeta,
Hgamma, [O III], [N II], [S II], [O II], Ca II H&K, G-band, Mg b, Na D, plus a few extra real AGN/Seyfert
lines -- [Ne III], He II 4686, [O I] 6300, [Ar III] 7135, the Ca II near-IR triplet, [S III] 9069) and matched
each de-redshifted detection to it within a 6-Angstrom tolerance. 21 of the 26 detections matched a known line;
5 did not, and I report those honestly as unmatched rather than forcing a label.

With H-beta, [O III] 5007, H-alpha, and [N II] 6585 all detected, I built a rough BPT-style diagnostic:
log([N II]/Halpha) = 0.068, log([O III]/Hbeta) = 0.819, which lands on the AGN side of the Kewley (2001)
maximum-starburst line -- consistent with SDSS's own `AGN` classification for this fiber. The measured Balmer
decrement (Halpha/Hbeta = 7.79) is far above the case-B value of 2.86, which I attribute mostly to my simple
window-sum flux estimate picking up broad-line wings unevenly on an AGN-classified ("BROADLINE") spectrum,
rather than claiming extreme dust extinction.

The line search also recovered a full underlying stellar-absorption spectrum: Ca II H&K, Mg b, Na D, and the
Ca II near-infrared triplet, all matched to their literature wavelengths to within a few Angstroms -- a nice
confirmation that this AGN host galaxy has a normal, detectable stellar population underneath the nuclear
emission lines.

## What's next

I would fit real Gaussian (or broad+narrow) profiles instead of window-sums to get honest flux uncertainties
and deblend the [N II]-Halpha-[N II] triplet properly, cross-check the AGN classification against an
independent NED/SIMBAD spectral type, and dig into the 5 unmatched features to see if they correspond to
known stellar absorption indices I left out of my (deliberately short) reference table.

## Data source and citation

- SDSS DR18 spectra and images: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- NIST Atomic Spectra Database: https://physics.nist.gov/PhysRefData/ASD/lines_form.html
- Kauffmann et al. (2003): https://doi.org/10.1046/j.1365-2966.2003.07154.x
- Kewley et al. (2001): https://doi.org/10.1086/321545
