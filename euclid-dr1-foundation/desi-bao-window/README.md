# BAO-scale pair retention in the Euclid–DESI overlap

**Biswajit Jana** · 20 November 2026

[Figure](results/euclid_desi_window.png) · [Measurements](results/window_measurements.json) · [Run in Colab](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation/desi-bao-window/DESI_Euclid_Pair_Window.ipynb)

## Question and result

How many pairs at the baryon acoustic oscillation (BAO) scale survive when the public DESI DR1 luminous red galaxy (LRG) sample is restricted to the Euclid DR1-Foundation footprint? Existing DESI work tests BAO across multiple sky regions, and a June 2026 presentation illustrates the Euclid–DESI overlap. Here the calculation applies two named public Euclid masks to official DESI galaxy and random catalogues and measures the resulting orientation-dependent pair loss.

| Redshift interval | DESI DR1 LRGs | LRGs in Euclid MER Wide Survey | LRGs in Euclid Wide tiles |
|---|---:|---:|---:|
| 0.4–0.6 | 506,911 | 1,686 | 3,474 |
| 0.6–0.8 | 771,894 | 2,795 | 5,350 |
| 0.8–1.1 | 859,822 | 2,886 | 5,876 |
| Total | 2,138,627 | 7,367 (0.344%) | 14,700 (0.687%) |

The MER footprint retained roughly 0.06–0.08% of the weighted DESI random pairs between 95 and 115 h⁻¹ Mpc, depending on the redshift interval. The broader tile geometry retained more pairs overall. It retained a smaller fraction of partners for a given endpoint in the overlap, especially for pairs lying across the sky.

The orientation effect persists in each redshift interval and both thinnings. For the MER mask, when one endpoint was inside, the partner also lay inside for roughly 32–47% of nearly transverse pairs (|µ| < 0.2) and 59–71% of nearly radial pairs (|µ| ≥ 0.8). Three approximately equal-area circular controls also lose more transverse than radial pairs, as expected for an angular cut. In the middle redshift interval they retain about 58–65% of transverse partners, compared with 40–41% for the MER mask. The controls have unequal DESI densities and are a comparison of geometries.

## Inputs and calculation

- Use the North and South Galactic Cap DESI DR1 LRG clustering galaxy files and random realisation 0 from LSScats v1.5. Use both endpoints in the same redshift interval with the upper edge excluded. The DR1 redshift catalogues are public. The DR2 cosmology results are public and the underlying DR2 redshift catalogues are pending. The [earlier DESI expansion fit](../euclid-dark-universe/) uses the published DR2 distance estimates.
- Restrict sky positions using the IRSA DR1 MER Wide Survey catalogue MOC and the more inclusive Euclid Wide tiles MOC. Both are angular footprints. This counts DESI LRG coordinates in those masks, without requiring Euclid catalogue detection or a successful Euclid spectrum.
- Estimate DESI angular support from the full random realisation in each cap. Intersect Euclid MOCs with cells containing positive-weight randoms at HEALPix NSIDE 128 and 256. One or more randoms at NSIDE 128 gives 88.8 deg² of MER overlap. The NSIDE 256 estimates are 74.6 deg² at one random and 71.3 deg² at five. The corresponding Wide-tile estimates are 149.4, 127.7, and 122.5 deg². Pixel occupancy gives a sampled area proxy whose value depends on resolution and occupancy threshold. Membership of galaxies and randoms in Euclid uses the original Euclid MOCs.
- Choose three compact spherical caps with nominal areas of 71.3 deg². Search the NSIDE 8 cell centres for caps that are at least 97% inside the NSIDE 256 five-random DESI support and disjoint from both Euclid masks. Start with the best supported cap and maximise minimum angular separation when placing the other two. Cap centres, pixelised areas and coverage fractions appear in the JSON. The same DESI catalogues are used in all regions.
- Exclude 2,551 random rows with non-positive weights. Form two disjoint Bernoulli thinnings from the same DESI random realisation, using a fixed generator seed. In each thinning, the inclusion probability is 1/4 inside any analysis mask and 1/32 elsewhere. The per-object weight is DESI `WEIGHT × WEIGHT_FKP` divided by that inclusion probability. Pair weights multiply the two corrected object weights. Oversampling the masks improves precision in the small overlap.
- Convert redshifts to comoving distances with flat ΛCDM and Ωm = 0.315 as a fixed coordinate convention. Count each unordered pair once at 95 ≤ s < 115 h⁻¹ Mpc in five bins of |µ|, the absolute cosine relative to the pair midpoint line of sight. Multiply the sum of pair weights with two endpoints inside a mask by two, and divide by the sum of weighted inside endpoints of all eligible pairs. This gives the fraction of partners inside given an endpoint inside. Weighted pair counts were checked against a brute-force calculation in all five orientation bins.
- The figure shows the mean between thinnings and the range between them. This range shows sensitivity to random thinning and does not estimate the uncertainty of a BAO fit. The grey range spans the three cap means.

## Scope

The result measures the selection of random pairs at a fixed separation range. It does not fit a clustering peak, constrain the Hubble rate, or determine a shift in the recovered BAO scale. The very low all-pair fraction and the orientation dependence quantify why a BAO fit on this overlap needs a dedicated validation. The direct test is to cut the same DESI galaxies, randoms and clustering mocks to each mask, fit the anisotropic peak across mock realisations, and compare the shifts and coverage of the fitted intervals. Adding Euclid spectroscopic or redshift-quality cuts will require a random catalogue that represents the Euclid selection. ESA schedules the Euclid clustering selection functions for complete DR1.

## Reproduction

Use Python 3.11 or newer with NumPy, SciPy, Astropy, astropy-healpix, mocpy, and Matplotlib. Allow approximately 1.72 GB for the public inputs. The downloader checks SHA-256 against [the recorded input list](input_files.json).

```bash
python fetch.py --cache /tmp/euclid-desi-window
python analyse.py --cache /tmp/euclid-desi-window
python plot_window.py --cache /tmp/euclid-desi-window
```

## References and acknowledgements

- Euclid Collaboration, Aussel et al. (2026), *Euclid First Data Release 1 (DR1). Data release overview*. [arXiv:2611.16510](https://arxiv.org/abs/2611.16510) · [IRSA archive](https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html) · [ESA Explanatory Supplement](https://euclid.esac.esa.int/dr/dr1/expsup/)
- DESI Collaboration (2026), *Data Release 1 of the Dark Energy Spectroscopic Instrument*. [arXiv:2503.14745](https://arxiv.org/abs/2503.14745) · [Clustering files and documentation](https://data.desi.lbl.gov/doc/releases/dr1/#large-scale-structure-catalogs)
- Ross et al. (2025), *The construction of large-scale structure catalogs for the Dark Energy Spectroscopic Instrument*. [JCAP 01, 125](https://doi.org/10.1088/1475-7516/2025/01/125)
- Andrade et al. (2025), *Validation of the DESI DR2 Measurements of Baryon Acoustic Oscillations from Galaxies and Quasars*. [arXiv:2503.14742](https://arxiv.org/abs/2503.14742)
- Porredon (2026), Euclid × DESI overlap overview. [Noirmoutier presentation](https://indico.ijclab.in2p3.fr/event/11873/contributions/41462/attachments/27813/41579/03_DESIcosmology_Anna_Porredon.pdf)

This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA), served by NASA/IPAC IRSA. This research used data obtained with the Dark Energy Spectroscopic Instrument (DESI), whose construction and operations are managed by Lawrence Berkeley National Laboratory. The DESI collaboration provides [the data licence and full acknowledgements](https://data.desi.lbl.gov/doc/acknowledgments/). ChatGPT assisted with archive queries, Python implementation, and figure preparation.
