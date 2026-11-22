# NCH-007

Biswajit Jana · Euclid Deep Field North

The VIS peaks are separated by 0.781″ at ICRS 274.3260348°, +64.5745918°. The pair ranked 13 in the fixed filter-score search.

[Image and visit plot](figure.png) · [Native and matched aperture results](photometry.json) · [Visit measurements](visits.json) · [Catalogue outputs](crossmatches.json) · [FITS inputs](target.json)

| Band | B − A aperture magnitude at 0.28″ |
|---|---:|
| VIS | +0.499 |
| J | -0.682 |
| H | -0.927 |
| i2 | +0.051 |

The primary VIS–J–H reversal **passes** in the native mosaics. It **passes** across the two approximate Gaussian PSF settings. The Subaru i2 check **does not pass** the expected optical order. 3 of 3 complete visit checks pass at all aperture radii.

### Catalogue and classification checks

- Peak A matches MER ID 2743259033645745227 at 0.096″.
- Peak B matches MER ID 2743262383645747132 at 0.187″.
- GAIA returned 0 matches inside the search radius.
- SIMBAD returned 0 matches inside the search radius.
- DESI returned 0 matches inside the search radius.
- The nearest published ECLIPSE entry is 2118.3″ away.
- 1 of 2 rank-zero SPE galaxy redshift proposals clear the illustrative IRSA cuts. A proposal alone cannot establish the redshift of each component in a close blend.

The rank-zero catalogue galaxy redshifts are 0.80354 for A and 0.80426 for B. The same NISP slitless data can contribute to both nearby extractions. Of the four exact-ID coadds and five fixed line windows per coadd, only the B blue-grism [S II] window passes the clean-pixel criterion. Its fitted S/N is −0.56. The available clean line windows leave the physical class open. [Line fit outputs](spectral_checks.json) · [Extracted public coadds](nisp_spectra.json.gz)

[Series methods and comparative results](../README.md)
