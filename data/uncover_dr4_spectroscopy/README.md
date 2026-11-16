# UNCOVER DR4.1 spectroscopy derivative

This directory freezes the public UNCOVER DR4.1 redshift, line-flux, lens-model,
and representative spectrum products used by the 1 August 2026 notebooks.
Rows with `flag_zspec_qual` 2 or 3 are described as solid or secure, following
the release. Line fluxes retain the release units and are **not** corrected for
lensing magnification. The six FITS files are the release's recommended default
1D/2D spectra, not the separately supplied photometric-rescaled variants.

The cross-match joins the earlier DR3 high-redshift candidate table on its
catalogue ID (`id`) and DR4's `id_DR3`. It is an audit of the photometric
selection, not a complete or random spectroscopic sample: NIRSpec targets were
selected for several science programmes and the unmatched candidates have no
spectroscopic verdict here.

Sources: the [official DR4.1 release](https://jwst-uncover.github.io/DR4.html),
Price et al. (2025), Suess et al. (2024), and the Furtak et al. lens model.
Exact file sizes and checksums are recorded in `manifest.json`.
