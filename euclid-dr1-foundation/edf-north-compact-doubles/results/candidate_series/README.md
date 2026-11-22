# Ten additional compact-pair investigations in Euclid Deep Field North

**Biswajit Jana** · 22 November 2026

Ten pairs at ranks 13–22 were drawn from the 36 reversals in the fixed filter-score screen of 1,135 held-out image pairs. These ranks were outside the twelve measured in the previous report.

4 of 10 pass the three-band native-aperture check. 3 pass both the approximate PSF-matching check and at least two separate visits. 1 of those also pass the independent Subaru i2 aperture-order test.

| Target | Separation | Native reversal | PSF-matched reversal | Subaru optical order | Passing / complete visits |
|---|---:|---|---|---|---:|
| [NCH-007](NCH-007/) | 0.781″ | yes | yes | no | 3/3 |
| [NCH-012](NCH-012/) | 0.800″ | yes | yes | yes | 2/2 |
| [NCH-091](NCH-091/) | 0.806″ | no | no | no | 0/3 |
| [NCH-066](NCH-066/) | 0.922″ | no | no | no | 0/3 |
| [NCH-158](NCH-158/) | 0.762″ | no | no | no | 0/3 |
| [NCH-028](NCH-028/) | 0.900″ | yes | yes | no | 0/3 |
| [NCH-117](NCH-117/) | 0.806″ | no | no | no | 0/2 |
| [NCH-052](NCH-052/) | 0.800″ | yes | yes | no | 3/3 |
| [NCH-133](NCH-133/) | 0.949″ | no | no | no | 0/3 |
| [NCH-078](NCH-078/) | 0.854″ | no | no | no | 0/2 |

## Leads and limits

**NCH-012** is the clearest imaging follow-up. The sign of the brightness difference agrees across the individually testable Euclid visits and independent Subaru imaging. Both image peaks match separate MER detections. Neither catalogue redshift proposal passes the illustrative IRSA reliability screen. The two usable Euclid visits are distinct observations. A third scheduled stack lacked a complete check.

**NCH-007** has two close pipeline galaxy-redshift proposals, at 0.80354 and 0.80426. One passes the illustrative IRSA probability and reliability cuts. Extracting the two grism coadds for each source yields one evaluable clean line window out of 20, with fitted signal-to-noise of −0.56. Close slitless traces can share light. The sky proximity and pipeline redshifts motivate follow-up, and the clean-spectrum check leaves their physical association open. [Exact-ID line checks](NCH-007/spectral_checks.json)

**NCH-028** is the sole case with one peak lacking a separate nearby MER centroid in the tested tile. Its mosaic reversal fails the separate-visit requirement. The unmatched peak remains unverified as a separate object.

## Methods and scope

- Reuse the published input positions and the earlier fixed ranking procedure. Remove the previously measured 12. Require no ECLIPSE entry within 3″ for inclusion. The selection concerns colour reversal.
- Register calibrated VIS, J, H and Subaru i2 mosaics to a 0.1″ north-up grid. The 81 × 81 FITS stamps preserve the central registered pixels and celestial axes. Photometry and its sky tests use the larger archive cutouts.
- Apply 0.20″, 0.28″ and 0.35″ apertures and the sky-difference test. All radii must preserve the expected VIS/J/H signs by more than five times a local background-difference scatter. This excludes blending and model uncertainty.
- Repeat after approximate Gaussian PSF matching at 0.65″ and 0.80″ using Euclid tile PSF headers. Select the first, middle, and last common VIS/J/H observation IDs and repeat the signed measurements at the fixed centroids.
- Check Gaia DR3, SIMBAD and DESI DR1 at each midpoint. Extract Euclid MER, PHZ and SPE rows using per-tile FITS files and associate a centroid to a VIS peak within 0.25″. Both components may contaminate each other's apertures or spectra.
- A stable image pair is a candidate for physical interpretation. These cuts establish brightness ordering in the images.

## Reproduce

Install the shared [requirements](../../requirements.txt) and run from the study directory.

```bash
python candidate_series.py --cache work/new-candidates
python package_candidate_series.py --cache work/new-candidates --output work/series-packets
python series_spectroscopy.py --cache work/new-candidates --candidate NCH-007 --output work/series-packets/NCH-007
```

This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA). The measurements use IRSA-hosted calibrated Euclid and Subaru WISHES imagery. [Euclid release and data DOI](https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html) · [ECLIPSE catalogue](https://doi.org/10.5281/zenodo.19654904) · [IRSA spectroscopy example](https://caltech-ipac.github.io/irsa-tutorials/euclid-intro-phz-catalog/)

ChatGPT assisted with archive queries, code, and figure preparation.
