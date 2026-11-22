# NCH-042 · A wavelength-dependent brightness reversal in Euclid Deep Field North

**Biswajit Jana** · 22 November 2026

[Image and repeat measurements](results/holdout_colour/NCH-042.png) · [Aperture measurements](results/holdout_colour/aperture_checks.json) · [Catalogue matches](results/holdout_colour/lead_catalogues.json) · [Run in Colab](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation/edf-north-compact-doubles/Euclid_DR1F_Holdout_Colour.ipynb)

## Result

**NCH-042** is an internal label for a 0.800″ pair centred at **ICRS 274.329313°, +64.489303°** (18:17:19.035, +64:29:21.493). The northern component A is brighter in Euclid VIS. The southern component B dominates Euclid J and H. The ordering repeats at all three aperture radii in three individual Euclid visit stacks from 14 June 2024 to 12 May 2025. An independent Subaru HSC i2 observation agrees with the VIS ordering. The Subaru image contributes an optical ordering check at fixed Euclid positions, given its broader point spread function.

| Image | B minus A aperture magnitude at radius 0.28″ |
|---|---:|
| Euclid VIS mosaic | +0.671 |
| Euclid J mosaic | −1.425 |
| Euclid H mosaic | −1.515 |
| Subaru HSC i2 mosaic | +0.417 |

The measured difference $(\mathrm{VIS}-J)_B-(\mathrm{VIS}-J)_A$ is **+2.096 mag** in the native-resolution mosaics. It spans +2.048 to +2.114 mag across the three aperture radii. Approximate Gaussian matching to common FWHM of 0.65″ and 0.80″ preserves the ordering and leaves a contrast of about **1.51–1.94 mag** across those aperture radii and target resolutions. These are aperture colour contrasts in a blend. Light from each component enters the other aperture.

The [visit measurements](results/holdout_colour/visit_checks.json) give B minus A between +0.67 and +0.71 mag in VIS, −1.43 and −1.31 mag in J, and −1.55 and −1.42 mag in H at the same aperture radius. NCH-042 has the strongest pre-photometry rank in the shortlist. Six of twelve shortlisted pairs pass the three-band brightness reversal at every preselected aperture radius. The shortlist deliberately favours reversals and cannot estimate their frequency in Euclid.

## Existing identifications and redshift evidence

Both components are already in the public Euclid MER catalogue, IDs **2743293130644894073** (A) and **2743293305644891810** (B). They share parent 2089 on tile 101830407 and both have the deblending flag set. Their MER coordinates agree with the measured VIS peaks within 0.026″ and 0.048″, respectively. The analysis independently characterises the pair using the calibrated pixels.

The public ECLIPSE object table has no match within 3″. The Gaia DR3 and SIMBAD searches returned no entry within 5″, and DESI DR1 returned no spectrum within 2″. Searches using the pair coordinates and exact MER IDs did not turn up a target-specific publication. This is a bounded catalogue and literature check. The public source detections predate this analysis and these searches cannot establish publication priority.

| Component | Euclid photometric redshift median | Rank-zero SPE galaxy redshift | SPE probability | SPE reliability |
|---|---:|---:|---:|---:|
| A | 1.48 | 1.57758 | 0.352 | 0.00689 |
| B | 1.25 | 1.35408 | 0.392 | 0.00272 |

Both slitless proposals fall below the illustrative IRSA high-quality cuts `SPE_Z_PROB > 0.99` and `SPE_Z_REL > 0.05`. Exact-ID SIR extraction returned two grism coadds for each component. Across the four coadds and five expected lines at each component's proposed redshift, **one of 20** fixed line windows passes the clean-coverage criterion. That [O III] window for A in the blue grism gives a formal amplitude S/N of **1.31**. Thus neither redshift is supported by this check. Shared pixels and overlapping slitless spectra limit physical interpretation.

A projected alignment and substructure in one galaxy remain plausible. The imaging result is the repeatable brightness reversal. Establishing the physical class requires reliable spatially resolved spectroscopy or a two-dimensional spectral extraction whose line assignments survive comparison across dispersion angles.

## Selection and measurement

- Start with [1,135 held-out VIS/J repeaters](results/holdout_repeaters.csv) from twelve previously searched Euclid Deep Field North mosaic crops. Screen at separation ≥0.75″, minimum VIS filter score ≥20, minimum J filter score ≥12, and J filtered saddle depth ≥0.20. Rank the 36 pairs with opposite VIS and J peak ordering by the log of the filter-score ratio change. The filter statistic defines the shortlist. Photometry uses unfiltered FITS pixels.
- Query the 26,662-row public ECLIPSE object catalogue and take the first 12 ranked systems without an ECLIPSE match inside 3″. Fetch and register VIS, J, H and Subaru HSC i2 MER cutouts. Exact image URLs, FITS header hashes, ETags and byte-range hashes are in the [selection output](results/holdout_colour/selection.json).
- Sum locally sky-subtracted flux at the two fixed VIS positions, using radii of 0.20″, 0.28″ and 0.35″ with subpixel aperture weights. A 2.5–5″ annulus supplies a clipped median sky. Estimate the scatter of the flux difference with a scaled median absolute deviation from translated aperture pairs. The three-band check requires the expected sign and a flux difference exceeding five times this background scatter at every radius. This selection statistic does not include blending, source photon noise, or calibration uncertainty.
- Use the Euclid catalogue PSF central-stamp FWHM values of 0.196″, 0.507″ and 0.557″ for VIS, J and H to test approximate Gaussian resolution matching in the lead cutout. The RGB display uses the 0.65″ setting and maps H/J/VIS to red/green/blue. The monochrome panels use separately stretched calibrated pixels with no extra PSF smoothing.
- Select the first, middle and last of 13 SIA observation IDs offering common VIS/J/H coverage for the lead. Observation IDs 2078, 5005 and 7798 are separate visit stacks. The mosaic can contain data from those visits and therefore is not an additional independent epoch.
- For spectroscopy, use the existing fixed-window local-continuum fits in [SPECTRAL_CHECK.md](SPECTRAL_CHECK.md). Record insufficient clean bins as unavailable rather than accepting masked flux as a detection.

## Reproduction

Use the study's `requirements.txt` and curl. Run from this directory with a writable scratch cache.

```bash
python holdout_colours.py --cache /tmp/holdout-colour
python measure_holdout_colours.py --cache /tmp/holdout-colour
python holdout_visits.py --cache /tmp/holdout-colour
python holdout_catalogues.py --cache /tmp/holdout-colour
python spectra.py --cache /tmp/holdout-colour/spectrum --results /tmp/holdout-colour/spectrum
python plot_holdout_lead.py --cache /tmp/holdout-colour --output /tmp/holdout-colour/NCH-042.png
```

The mosaic and visit windows read about 432 MB of FITS ranges. The catalogue and spectrum steps add further reads. Use the committed figure and JSON files for inspection without repeating the downloads.

## Data references

- Euclid Collaboration (2026), *Euclid First Data Release 1*. [Release overview](https://arxiv.org/abs/2611.16510) · [IRSA archive and data DOI](https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html)
- Euclid and Subaru WISHES imaging. [MER documentation](https://euclid.esac.esa.int/dr/dr1/dpdd/merdpd/merintro.html) · [MER multiwavelength mosaics](https://doi.org/10.26131/IRSA683)
- Euclid spectroscopy. [DR1 spectroscopic performance](https://arxiv.org/abs/2611.17960) · [SIR combined spectra specification](https://euclid.esac.esa.int/dr/dr1/dpdd/sirdpd/dpcards/sir_combinedspectra.html) · [IRSA reliable-redshift example](https://caltech-ipac.github.io/irsa-tutorials/euclid-intro-phz-catalog/)
- Lines et al. (2026), ECLIPSE. [Paper](https://arxiv.org/abs/2611.15883) · [Public object catalogue](https://doi.org/10.5281/zenodo.19654904)

This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA). NASA/IPAC IRSA serves the Euclid and ancillary Subaru WISHES data used here. ChatGPT assisted with archive queries, Python implementation and figure preparation.
