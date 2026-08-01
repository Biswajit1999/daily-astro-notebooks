# UNCOVER DR3 high-redshift working table

`uncover_dr3_z6_candidates.csv` is a compact derivative of the recommended
UNCOVER DR3 “SUPER” photometric catalogue (Zenodo DOI
[`10.5281/zenodo.11059273`](https://doi.org/10.5281/zenodo.11059273)). The full
catalogue contains 74,020 sources over the Abell 2744 field. This derivative
retains 4,731 rows satisfying `use_phot == 1`, `flag_eazy == 1`, and
`6 <= z_phot < 15`, plus only the coordinates, flags, redshift posterior,
lensing, morphology, and seven broad-band photometry groups used in Batch 9.

Fluxes and errors are in the catalogue's native `10 nJy` units, corresponding
to an AB zeropoint of 28.9. The selection means that the photometry is usable
and the EAzY fit passed the release flag; it does **not** make every row a
spectroscopically confirmed high-redshift galaxy. The notebooks therefore use
the phrase *photometric high-redshift candidate* and test sensitivity to the
redshift-posterior width.

Run `python tools/prepare_uncover_highz.py` to reproduce the CSV from the full
FITS product. The script checks the upstream MD5 checksum recorded by Zenodo,
writes `manifest.json`, and removes the large temporary download.

Please cite Suess et al. (2024), Weaver et al. (2024), Bezanson et al. (2024),
and the UNCOVER release when reusing this product. The UNCOVER site now also
hosts DR4 spectroscopy and updated lensing products; this frozen DR3 table is
used because its photometry and EAzY posterior columns form one internally
consistent public release.
