# mast

MAST archive — Hubble, JWST, Kepler, TESS images and light curves.

Each dated subfolder here is one self-contained real-data analysis.

The newest five notebooks form an UNCOVER high-redshift candidate series:

- candidate-count sensitivity to photometric-redshift posterior width;
- median HST/JWST broad-band stacks and Lyman-break migration;
- Abell 2744 magnification and approximate intrinsic F444W flux;
- catalogue half-light-radius proxies with explicit PSF and shear limits;
- spatial selection against F444W image weight and lensing structure.

They use a 1.7 MB, 4,731-row derivative of the public DR3 “SUPER” catalogue.
These are photometric candidates, not new spectroscopic confirmations. The
named next validation is a match to UNCOVER DR4.1 spectra and lens model v2.0.

The 2026-08-03 batch adds six combined imaging/photometry/spectroscopy notebooks:

- NGC 1068 (M77): a real HST/WFC3 image plus a joined HST/STIS G430L+G750L
  spectrum, with automated peak detection matched against a literature AGN
  emission-line table (7 of 14 lines recovered, spanning H, N+, O++, Ne++, S++).
- 47 Tucanae: five real, cross-matched HST/ACS filters (F435W-F814W) building a
  genuine color-magnitude relation, with an honest note that the quality cuts
  used exclude the bright red-giant branch from this particular clean sample.
- Eagle Nebula pillars: a real HST-vs-JWST point-source sharpness comparison
  against the diffraction limit, showing wavelength can beat aperture size.
- Crab Nebula: an honest non-detection of filament proper motion between two
  real HST epochs 9 years apart, with a sensitivity check showing why.
- M51: a two-filter (F435W/F814W) color-difference map that recovers the
  galaxy's real dust-lane structure from real, uncalibrated preview imagery.
- RR Lyrae: a blind TESS period search recovering the star's known 0.5668-day
  pulsation to within 2.4 seconds, plus an exploratory Blazhko-effect check.

The 2026-08-04 batch adds two more:

- SS Cygni: five real TESS epochs (2019-2024) of the prototype dwarf nova, with
  a from-scratch outburst detector recovering 9 real outbursts and 4 direct
  recurrence-time measurements checked against the published historical range.
- NGC 6397: a from-scratch DAOStarFinder-plus-aperture-photometry pipeline run
  directly on real HST/ACS pixels (not a catalog pull), recovering a clean
  color-magnitude diagram, validated to 0.05 mag scatter against MAST's own
  point-source catalog, with a real artificial-star completeness test.
