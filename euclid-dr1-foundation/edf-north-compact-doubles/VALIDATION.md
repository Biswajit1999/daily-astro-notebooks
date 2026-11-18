# Empirical resolution and spectroscopy checks

**Research author:** Biswajit Jana
**Date:** 18 November 2026

## Aim

Quantify the effect of angular separation on the chance that both VIS peaks recur in NISP J. Assess the role of the measured J point-spread function by adding controlled pairs to observed sky backgrounds. For EDN-004, test the persistence and possible identity of the line at 13155.55 Å.

## Findings

- In the held-out tiles, the wide-minus-narrow recovery difference was 22.0 percentage points after matching on tile, the weaker VIS peak score, and the filtered peak-amplitude ratio. The 10,000-resample whole-tile interval was 20.0–24.0 points. This is a within-field descriptive interval.
- The J point-spread profiles come from 298 selected Gaia DR3 stars. Tile-median Gaussian core FWHM spans 0.500–0.506 arcsec. Of 11,664 double injections, the nominal-PSF case with a half-bright companion and isolated 10-MAD strength gives 37/108 and 108/108 at 0.60 and 0.70 arcsec respectively. No empty or single-source placement passed out of 648 trials of each kind on the selected backgrounds.
- EDN-004 component A retains two blue exposures above formal S/N 4 across all three tested widths after removing the highest central bin. One red exposure at 180 degrees passes at widths 12 and 16 Å. Only three predicted additional-line windows are usable, and the highest positive S/N is 1.89. The slitless feature therefore still has multiple plausible identifications.

These tests were designed after the original imaging result. Quiet backgrounds and compact injected stellar profiles define the scope of the injection test. Reusing stamps gives correlated placements. The analysis does not derive a physical pair fraction or a whole-survey completeness estimate.

## Reproduce

The 25-cell Colab notebook reads the published measurements and runs the matched estimate, injection experiment and exposure fits. Its default analysis uses the bundled observations. An optional cell reprocesses selected archive tiles. Run the same pieces directly from this directory with Python 3.12 and the packages in requirements.txt.

- matched_recovery.py freezes testable rows from both runs and performs the common-support analysis.
- injection_inputs.py builds stellar templates and quiet backgrounds from the stored Euclid FITS ranges and Gaia DR3 queries.
- inject_pairs.py reruns all placements on the supplied background stamps and profiles.
- edn004_recheck.py takes the original two FITS products or uses the supplied exposure arrays, tests alternative line widths and records coverage at diagnostic redshifts.
- line_fits.py is the common weighted continuum and Gaussian line fit.
- The validation_data directory contains provenance, public archive paths and checksums, measured stars, extracted spectral arrays, tabular results, and figures.

The notebook headings, metadata and report identify Biswajit Jana as research author. Data credits are retained in the notebook and report.
