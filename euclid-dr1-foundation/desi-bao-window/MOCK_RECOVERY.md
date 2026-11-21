# Acoustic-peak recovery in the Euclid–DESI overlap

**Biswajit Jana** · 21 November 2026

[Figure](results/mock_recovery.png) · [Pair counts, fits and input hashes](results/mock_recovery.json) · [Run in Colab](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation/desi-bao-window/DESI_Euclid_Mock_Recovery.ipynb)

## Question

Can a simple acoustic feature be recovered at a consistent separation when the same DESI DR1 mock catalogues are restricted to the released Euclid MER Wide footprint? The [earlier pair-count study](README.md) found 2,795 observed DESI luminous red galaxies inside that footprint at (0.6 le z < 0.8). This follow-up compares the correlation function in the full DESI window with the same mock realisations after the Euclid cut.

## Results

| Mock window | Median galaxies used | Mean bump amplitude (×10⁻³) | 95% bootstrap interval (×10⁻³) | Mock-to-mock SD (×10⁻³) | Free fits at scan edge |
|---|---:|---:|---:|---:|---:|
| Full DESI window, thinned | 353,627 | 3.55 | 3.09 to 4.04 | 0.73 | 0/8 |
| Euclid MER overlap | 8,437 | 3.31 | −4.46 to 10.15 | 11.47 | 4/8 |
| Euclid MER overlap, observed count | 2,795 | 3.48 | −7.07 to 13.78 | 16.12 | 3/8 |

One count-matched mock had no positive free bump at any scanned centre. Every full-window centre landed between 99.5 and 106.5 h⁻¹ Mpc. The scatter of the fixed-centre amplitude was 15.6 times the thinned full-window value after the Euclid cut and 22.0 times after matching the observed count. Paired bootstrap intervals for the mean change include zero in all five fixed-centre/width settings. The cut therefore makes this diagnostic substantially less repeatable, while the eight-mock sample leaves a systematic shift unresolved.

After injecting a known centre into the held-out correlation-function residuals, the number of recovered centres within 8 h⁻¹ Mpc was:

| Injected centre (h⁻¹ Mpc) | Full DESI window | Euclid overlap | Overlap, observed count |
|---|---:|---:|---:|
| 96 | 8/8 | 1/8 | 1/8 |
| 104 | 8/8 | 3/8 | 3/8 |
| 112 | 8/8 | 4/8 | 3/8 |

## Data and estimator

- Use public DESI DR1 AbacusSummit v4.2 dark LRG mocks 0–7, North and South Galactic Caps, and their matched random realisation 0. The `complete` variant keeps targets reachable by a DESI fibre and omits the fibre-assignment step. The real catalogue can therefore have a lower density. Retain (0.6 le z < 0.8) and finite positions with positive catalogue weights.
- Apply the exact [IRSA MER Wide Survey catalogue MOC](input_files.json) from the earlier measurement. Use it on galaxies and randoms. The uncut calculation uses uniform Bernoulli draws retaining 25% of the mock galaxies and 5.5% of their randoms for computation. Uniform inclusion probabilities cancel within the separately normalised pair counts. Keep every eligible row inside the overlap, then draw one additional 2,795-galaxy sample per mock in that window. Keep its full masked random catalogue. This matches the observed count. The draw does not reconstruct angular fibre assignment or guarantee the observed redshift distribution.
- Convert redshifts to comoving positions using the same flat ΛCDM coordinates as the earlier calculation, with Ωm = 0.315. Compute the weighted Landy–Szalay statistic `(DD − 2DR + RR) / RR`, in 13 bins of width 8 h⁻¹ Mpc over 48–152 h⁻¹ Mpc. Each normalised count uses the corresponding total pair weight and products of the DESI `WEIGHT` and `WEIGHT_FKP` columns. The auto-pair normalisation excludes self pairs. The estimator pools orientations within each separation bin.
- Fit three smooth terms proportional to (1), (1/s) and (1/s^2), plus a Gaussian acoustic bump. The primary diagnostic has a fixed centre of 104 h⁻¹ Mpc and a width (sigma = 10) h⁻¹ Mpc. Amplitudes can be negative. Test centres of 100 and 108 h⁻¹ Mpc and widths of 8 and 12 h⁻¹ Mpc separately. A second fit scans 84–124 h⁻¹ Mpc in steps of 0.25 h⁻¹ Mpc with a nonnegative bump. A fit at either edge flags that the location is poorly determined in the chosen scan. Where every scanned amplitude clips to zero, record an absent centre.
- Bootstrap the mean fixed-centre amplitude with 10,000 draws from the eight simulated realisations, preserving the window pairings. Also quote the sample standard deviation across mocks. The fit uses equal bin weights. The intervals describe the scatter of this fixed diagnostic and do not represent a BAO likelihood.
- For the centre-injection check, subtract the mean of the other seven correlation functions from each held-out mock in each window. Add a Gaussian at a known centre with amplitude calibrated from the other seven full-window mocks. Use the same fitted-width convention and count fits within one 8 h⁻¹ Mpc bin of the injected centre. This injection is in correlation-function space. It checks separation recovery against the measured mock residuals and skips galaxy-level reconstruction. The three tests reuse the same eight realisations.

## Scope

The full-window fit is a reference within the same mock ensemble. The overlap comparison combines the smaller sky area, the angular geometry and the change in available pair counts. It uses one photometric footprint as an angular mask and does not model Euclid spectroscopic completeness. A cosmological inference would require a calibrated correlation template, covariance from a much larger mock ensemble, and a test of the angular dependence of the acoustic scale. The related Euclid cluster study tests matched galaxy-cluster and random masks with a DR1-like selection. The present project concerns simulated DESI luminous red galaxies in the cross-survey overlap.

## Reproduction

Use Python 3.11 or newer, NumPy, SciPy, Astropy, astropy-healpix, mocpy, Matplotlib and curl. The run streams approximately 11.5 GB, reduces it in FITS row blocks, and saves roughly 100 MB of filtered arrays. Every source URL, byte count and SHA-256 is in the results. The Euclid mask hash is checked against the previous study. Weighted tree counts were checked against brute-force pairs. The FITS stream reader was checked against an Astropy fixture and the fitting routine against a known injected bump.

```bash
python fetch_mocks.py --cache /tmp/abacus-lrg
OPENBLAS_NUM_THREADS=1 python mock_recovery.py --cache /tmp/abacus-lrg
python plot_mock_recovery.py
```

## References

- Maksimova et al. (2021), *AbacusSummit*, MNRAS 508, 4017–4037. [Paper](https://doi.org/10.1093/MNRAS/STAB2484) · [DESI mock archive and data model](https://data.desi.lbl.gov/doc/releases/dr1/#lss-mock-catalogs)
- DESI Collaboration (2026), *Data Release 1 of the Dark Energy Spectroscopic Instrument*. [arXiv:2503.14745](https://arxiv.org/abs/2503.14745) · [DESI BAO and full-shape products](https://data.desi.lbl.gov/doc/releases/dr1/vac/full-shape-bao-clustering/)
- Landy & Szalay (1993), *Bias and variance of angular correlation functions*, ApJ 412, 64. [NASA ADS](https://ui.adsabs.harvard.edu/abs/1993ApJ...412...64L/abstract)
- Euclid Collaboration (2026), *Euclid First Data Release 1*. [arXiv:2611.16510](https://arxiv.org/abs/2611.16510) · [Photometric masks](https://arxiv.org/abs/2611.16602) · [Survey mask effects on clustering of galaxy clusters](https://arxiv.org/abs/2611.06304)

This work uses public ESA Euclid DR1-Foundation data served by NASA/IPAC IRSA and public DESI DR1 simulation products. [DESI licence and acknowledgements](https://data.desi.lbl.gov/doc/acknowledgments/). ChatGPT assisted with archive queries, Python implementation, and figure preparation.
