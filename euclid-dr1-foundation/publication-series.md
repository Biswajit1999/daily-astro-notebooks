# Euclid DR1-Foundation open-data series

Biswajit Jana · 16 November 2026

The day numbers below are the order for sharing this work. The original research dates remain in the linked reports. Days 1–3 document one investigation in Euclid Deep Field North. Day 7 is a follow-up to the nearby-galaxy search.

| Day | Question or check | Evidence to share | Independent observations and limits |
|---|---|---|---|
| 1 | Does measured Hα strength track optical aperture size in a pilot field? | [Day 1 PDF](2026-11-14-day01/report/Euclid_Day_1.pdf) | The 426-object pilot uses Euclid imaging and spectroscopy. Only 150 of 327 matched sources pass the imaging cuts, below the predefined minimum of 200. |
| 2 | Does the apparent size difference persist with a direct VIS aperture and whole-tile resampling? | [Day 2 PDF](2026-11-15-day02/report/Euclid_Day_2.pdf) · [Euclid and Subaru image](2026-11-15-day02/analysis/targets/pair/Euclid_pair_RGB.png) | DESI DR1 provides independent redshifts for a subset. Subaru HSC i2 shows both galaxies in the close pair. It does not resolve the nature of the faint extension. The direct VIS interval spans zero. |
| 3 | How much of the nominal NISP wavelength overlap is usable for Hα? | [Day 3 PDF](day03-cross-grism/report/Euclid_Day_3.pdf) · [Example spectra](day03-cross-grism/analysis/example_spectra.png) | Two warning-inclusive detections survive re-centring on independent DESI redshifts. Neither also passes the red peak-bin removal check. |
| 4 | Do UV knots near NGC 4236 have matching optical structure? | [NGC 4236 PDF](ngc4236-uv-optical/report/NGC4236_UV_VIS.pdf) | GALEX UV and Euclid VIS probe different light. Gaia astrometry flags one foreground optical counterpart. SINGS narrow-band and R cover 10 of 23 exterior candidates. |
| 5 | Can Euclid aperture colours help identify two visually similar Carousel Lens arcs? | [Observed Euclid image](carousel-lens-colours/figures/carousel_euclid.png) · [Research note](carousel-lens-colours/) | Published HST modelling and VLT/MUSE spectroscopy distinguish the two background sources. A known same-source pair shows a colour contrast comparable to that of the distinct pair. |
| 6 | Do faint residual patches around nearby galaxies recur across instruments? | [Euclid and DECam comparison](nearby-galaxy-outskirts/figures/elongated_checks.webp) · [Research note](nearby-galaxy-outskirts/) | Four elongated patches rank highly at the same position in restored Euclid VIS, Legacy DR10 DECam r and Euclid H. Their morphology permits contributions from the host disc or blended sources. |
| 7 | Do the two IC 1914 patches survive a more flexible disc fit? | [Image and residual maps](nearby-galaxy-outskirts/ic1914-disc-fit/disc_residuals.webp) · [Research note](nearby-galaxy-outskirts/ic1914-disc-fit/) | Both optical patches exceed every control aperture after modelling broad asymmetry. The northern patch is stronger in H. Published ATCA H I imaging gives disc-scale context and cannot resolve the optical patches individually. |

## Distance examples from published spectroscopy

At the independent DESI redshift of 0.905244 in the Day 3 report, Planck18 gives a line-of-sight comoving distance of 3.15 Gpc, a luminosity distance of 6.01 Gpc, and a lookback time of 7.53 Gyr. The Day 3 report does not quote the redshift uncertainty used here, so this example gives point estimates.

The Day 5 VLT/MUSE redshifts of 0.96196 and 0.96154 each round to about 3.30 Gpc in comoving distance and 7.78 Gyr in lookback time. The small difference between those redshifts includes possible relative line-of-sight velocities and does not measure the galaxies' physical separation. For the reported uncertainty intervals on redshift, the table propagates the quoted endpoints at fixed cosmology. Cosmological parameter uncertainties and peculiar velocities are excluded. [Calculated table](distance_examples.csv) · [Reproduction script](distance_examples.py) · [Astropy Planck18](https://docs.astropy.org/en/stable/api/astropy.cosmology.realizations.Planck18.html)

Colour and magnitude can screen unusual objects or constrain photometric redshift when fitted across multiple calibrated bands. The distance examples above use spectroscopy. Nearby targets and foreground stars require an applicable distance indicator, such as a published redshift-independent distance or a reliable parallax.
