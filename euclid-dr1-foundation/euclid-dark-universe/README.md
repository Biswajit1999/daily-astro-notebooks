# Projected mass and cosmic acceleration with public observations

**Biswajit Jana · 18 November 2026**

## Aim

Measure a lensing mass scale in an overlapping cluster field, test whether selected public Euclid lens models exceed their fitted stellar budgets under conservative assumptions, and test acceleration with a separate set of published distance measurements.

## Results

- Ten sectors of the confirmed DES J0330-5228 arc give a 6.06 arcsec median ridge in Euclid VIS and 6.22 arcsec in Blanco DECam g. The arc source has published Gemini redshift 1.4541. At the background deflector redshift of 0.44, the one-plane circular mass proxy is 9.04e12 solar masses, 7.88 times the mass obtained by assigning the same angle to foreground Abell 3128 at z = 0.058. The sector range and lens-model caveats are in the report.
- Of 2,161 vetted public ECLIPSE models with stellar fits, 193 have a simple mass proxy above the upper fitted total stellar mass after lowering the radius and photo-z. Allowing another 0.30 dex of stellar mass leaves 26. Zero of 30 systems in the DESI-redshift overlap clear the same allowance. This is a candidate and sensitivity analysis. Gas masses, external convergence and alternative modelling remain open.
- The 13 published DESI DR2 BAO distances prefer accelerating Lambda-CDM among the tested expansion histories. With a free common ruler scale and curvature, chi-square is 9.95 for the unrestricted fit and 173.28 when q0 is constrained to be non-negative. The galaxy-only direction of the result agrees. This is a DESI result.

## Validation and RGB image

The [observed RGB figure](results/Abell3128_RGB.png) combines Euclid NISP H, Euclid VIS and Blanco DECam g. Channel gains and stretch are documented for visual reproduction. The scientific plots and report text use grayscale.

The arc extraction gives a VIS radius of 5.81–6.32 arcsec across 306 settings. The combined extraction and z = 0.42–0.46 sensitivity envelope is 7.88–10.37 trillion solar masses in the circular one-plane model. The catalogue stress test leaves seven models after allowing +0.30 dex in stellar mass, a uniform external convergence of 0.10 and gas equal to 25% of the enlarged stellar budget. Gas and convergence here are scenario inputs.

For DESI DR2, the curved q0 profile gives a delta chi-square = 1 interval from −0.569 to −0.505. Seven separate omit-one-redshift fits give q0 from −0.553 to −0.507.

## Reproduce

Open the notebook or run these commands from this directory:

    python -m pip install -r requirements.txt
    python acquire_public.py inputs
    mkdir -p results
    python arc_geometry.py inputs results
    python lens_budget.py inputs results
    python bao.py inputs/bao_mean.txt inputs/bao_cov.txt results/bao_fits.json
    python figures.py results
    python rgb_composite.py inputs results
    python robustness.py inputs results
    python make_note.py results Euclid_Dark_Universe_Research_Note.pdf

The archive view includes four calibrated MER cutouts of 491 by 491 pixels. The catalogue analysis reads the 15,072-row public physical-properties table. The compressed BAO fit uses the 13 published distances with covariance, without reprocessing individual DESI galaxy spectra.

The bundled original small catalogue archives and FITS cutouts support an offline replay. The acquisition script records URLs and checksums, while the image manifest records the exact FITS byte ranges. Raw XMM observations were not re-reduced. The report lists the independent published redshift checks and labels the test as a single-plane mass proxy. ECLIPSE catalogue construction includes machine learning and human inspection. This project uses classical calculation and fits applied to the public catalogue and images.

## Sources

- [Euclid DR1-Foundation](https://euclid.esac.esa.int/dr/dr1/expsup/)
- [ECLIPSE catalogue](https://doi.org/10.5281/zenodo.19654904)
- [Werner et al. 2007](https://arxiv.org/abs/0708.3253)
- [Nord et al. 2016](https://arxiv.org/abs/1512.03062)
- [McCleary et al. 2015](https://arxiv.org/abs/1503.02823)
- [DESI DR2 BAO](https://data.desi.lbl.gov/doc/papers/dr2/)
