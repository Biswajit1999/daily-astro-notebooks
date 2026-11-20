# Central colours of six dwarf candidates in Euclid Deep Field North

**Biswajit Jana** · 20 November 2026

[Three-page figure set](results/Euclid_EDF_North_Dwarf_Colours.pdf) · [Measurements by object and setting](results/colour_measurements.json) · [Run in Colab](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation/edf-north-dwarf-colours/EDF_North_Dwarf_Colours.ipynb)

## Results

Marleau et al. (2026) published 2,674 Q1 dwarf candidates and classified central blue clumps by visual inspection. This pilot measures central-minus-annular VIS−H colours on DR1-Foundation mosaics for three previously tagged candidates and three nearby catalogue controls. Negative values indicate a bluer centre in these two bands.

| Figure panel | Q1 classification | Centre minus annulus (mag) | Local background scatter (mag) | PSF and sky range (mag) | Outer-quadrant omission range (mag) |
|---|---|---:|---:|---:|---:|
| A1 | Blue-core tag | −0.213 | 0.016 | −0.237 to −0.166 | −0.217 to −0.210 |
| A2 | Control | +0.106 | 0.015 | +0.078 to +0.132 | +0.098 to +0.116 |
| B1 | Blue-core tag | +0.010 | 0.005 | −0.015 to +0.033 | +0.008 to +0.014 |
| B2 | Control | +0.123 | 0.009 | +0.086 to +0.150 | +0.119 to +0.129 |
| C1 | Blue-core tag | −0.869 | 0.044 | −0.894 to −0.786 | −1.023 to −0.554 |
| C2 | Control | −0.019 | 0.036 | −0.046 to +0.007 | −0.028 to −0.014 |

A1 and C1 stayed negative across all 12 PSF and sky combinations. The sign of B1 varied. C1 has an obvious red neighbour near the outer aperture. Dropping one outer quadrant at a time at the baseline setting preserved the sign and changed the estimate by as much as 0.32 mag. The corresponding changes in A1 were under 0.005 mag. Each tagged object's contrast was more negative than its matched control under all 12 common settings. The pairs were selected for a measurement pilot. Their contrasts cannot establish a population fraction or infer a physical cause such as recent star formation.

## Data and measurements

- Select from the published Q1 catalogue, Tables 1, 2 and 5. Require a dE classification, no disturbance tag, VIS magnitude 17.5–21.0, and apparent catalogue area ≥12 arcsec². Prefer tagged candidates with a published spectroscopic cross-match, then select in apparent-magnitude order. Pair each with an unused, untagged source within 0.30° (local tangent-plane separation), 0.45 mag, and a factor of two in catalogue area. Minimise the sum of the absolute magnitude difference and absolute log area ratio. The matching uses apparent properties.
- Retrieve 361 × 361 pixels in each of VIS, NISP Y and NISP H from the named public MER background-subtracted deep mosaics. Choose the tile offering the greatest minimum distance to its image edge among the candidates returned by IRSA. Use the FITS astrometry to register the images to a common north-up 0.1″ grid with bilinear interpolation and adopt the supplied magnitude zeropoints. The two input JSON files record mosaic and PSF product names, ETags and SHA-256 checks.
- The baseline Gaussian smoothing uses each tile's central catalogue PSF stamp FWHM to approximate a common resolution of 0.70″. The recorded central-stamp values span approximately 0.20″ in VIS, 0.48–0.50″ in Y, and 0.55–0.57″ in H. Subtract a sigma-clipped median in the 5–7″ sky ring and integrate net flux inside 0.8″ and from 1.5″ to 3.0″. Compute the difference of the two aperture colours from the VIS/H flux ratios.
- Repeat at 0.70″ and 0.95″, with the VIS and H model widths unchanged or shifted by ±0.05″ in opposite directions, and with 5–7″ and 7–9″ sky rings. These 12 settings test plausible changes in smoothing and sky subtraction. For the outer-quadrant test, omit each outer-annulus quadrant in turn at the baseline setting. All images are measured at the published catalogue position.
- Estimate local background scatter by placing the two apertures at 12 evenly spaced positions 12″ from each candidate. Reject placements with aperture flux outliers in either band. Propagate the joint flux variations through a local linear approximation to the colour difference and report the robust scatter of those projected values. Between 9 and 11 placements survive per object. These estimates omit galaxy shot noise and cannot capture all crowding or background errors. The Gaussian model approximates the tile-centre FWHM. Local PSF shape, additive backgrounds, catalogue centring, and overlapping sources remain limitations.
- Figure 1 uses a common asinh stretch of H, Y and VIS in the red, green and blue channels. Its pixel values come from the calibrated FITS mosaics. Figure 2 uses VIS without additional PSF smoothing for the optical detail and marks all three photometry radii. Figure 3 shows the photometry and its sensitivity to analysis choices.

## Connection to cosmic expansion and dark matter

The existing [DESI DR2 BAO analysis](../euclid-dark-universe/) fits 13 published distance estimates and provides a benchmark for expansion. An expansion measurement uses a three-dimensional galaxy distribution built from positions and redshifts. Baryon acoustic oscillations supply a standard ruler. The radial observable is D_H/r_d = c/[H(z)r_d], so a ruler calibration is needed to turn it into an absolute H(z). The redshift dependence of radial and transverse distances constrains dark-energy models.

A concrete survey test is to measure how Euclid's actual sky footprint and redshift-quality cuts change recovery of a known BAO scale. Start with DESI galaxies, random catalogues and matched mocks, apply the same Euclid footprint to the corresponding galaxies, randoms and mocks, and compare recovered distances and errors to area-matched control windows. Any follow-on Euclid-only measurement needs a sufficiently complete redshift sample and validated selection functions, random catalogues and covariance. IRSA and ESA list the cosmology-level clustering and weak-lensing products for the complete DR1 release.

Dwarf-galaxy colours trace light. An individual dwarf dark-matter mass inference needs dynamical tracers such as stellar line-of-sight velocities or a resolved gas rotation curve, along with a baryonic mass model. A redshift catalogue match on its own supplies neither internal velocity dispersion nor a rotation curve. Weak lensing can constrain projected total mass statistically. This six-object study measures colour gradients only.

## Reproduction

Run the commands below from this directory in a Python environment with NumPy, SciPy, Astropy and Matplotlib.

```bash
python fetch_cutouts.py --cache /tmp/edf-n-dwarfs
python fetch_psf.py --cache /tmp/edf-n-dwarfs
python measure_colours.py --cache /tmp/edf-n-dwarfs --output /tmp/edf-n-dwarfs/results
```

The fetch scripts validate the supplied manifests on download. The atlas takes roughly 270 MB of remote range reads and keeps approximately 9 MB of pixel cutouts. For source selection, download the [VizieR TSV export](https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J%2FA%2BA%2F711%2FA10&-out.max=4000&-out.all=1) and run `python select_targets.py catalog.tsv --output targets.json`. The optional `query_tiles.py --cache ...` refreshes the IRSA SIA queries when selecting inputs for a new run.

## References and credits

- Marleau et al. (2026), *Euclid Quick Data Release (Q1). X. A census of dwarf galaxies across a range of distances and environments*, A&A 711, A10. [Article](https://doi.org/10.1051/0004-6361/202554547) · [Catalogue](https://doi.org/10.26093/cds/vizier/bc-p7/lba)
- Euclid Collaboration, Aussel et al. (2026), *Euclid Data Release 1 (DR1). Data release overview*. [Release paper](https://pubs.euclid-ec.org/public/dr1/aussel.pdf) · [Euclid DR1 archive](https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html) · [Multiwavelength mosaic DOI](https://doi.org/10.26131/IRSA683) · [ESA Explanatory Supplement](https://euclid.esac.esa.int/dr/dr1/expsup/)
- DESI Collaboration (2025), *DESI DR2 results. II. Measurements of baryon acoustic oscillations and cosmological constraints*, Phys. Rev. D 112, 083515. [Article](https://doi.org/10.1103/tr6y-kpc6)

This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA). The images were served by NASA/IPAC IRSA. ChatGPT assisted with archive queries, Python implementation, and figure preparation.
