# 2026-11-19 — DR1-Foundation spectroscopy intake and blocked test

Biswajit Jana · research operations note, **not** a new numbered science day

## Archive and literature screen (19 November 2026)
Checked the 12 November 2026 ESA DR1-Foundation Explanatory Supplement, IRSA DR1 overview and product inventory, Euclid DR1 survey paper (arXiv:2611.17040), the July 2026 SIR processing paper (A&A 711 A6), and targeted web/arXiv search for DR1 emission-line studies. This is a limited title/abstract and documentation screen, **not** an exhaustive ADS bibliography or a novelty determination. DR1-Foundation includes SPE lines and SIR 1D spectra. Do not substitute forthcoming full DR1 high-level clustering products.

Sources:
- https://euclid.esac.esa.int/dr/dr1/expsup/
- https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html
- https://irsa.ipac.caltech.edu/euclid-archive-documentation/data-products/
- https://doi.org/10.26131/IRSA692
- https://doi.org/10.26131/IRSA680
- https://arxiv.org/abs/2611.17040
- https://doi.org/10.1051/0004-6361/202554627

## Proposed distinct falsifiable test (preregistered, NOT executed)
**Title:** Do nominal single-line redshifts in a fresh Euclid Deep Field South footprint survive an independent line-identity and grism-overlap check?

Freeze the footprint only after confirming available SIR and SPE tile identifiers: a 0.05-degree-radius ICRS cone centred on RA 63.0 deg, Dec -47.0 deg (provisional location, not yet verified as covered). Require primary MER exact-ID matches, usable red/blue grism coverage, finite variance and unmasked bins. Comparison sample: all quality-passing multi-line objects in the same cone; reject the test as underpowered if fewer than 20 multi-line controls. Rank single-line cases by formal integrated S/N and repeat-grism support, then downgrade any with plausible alternate rest-line identifications, overlaps, edge masks or visit disagreement. The falsifiable null is that the fraction of quality-passing single-line cases with independent corroboration is indistinguishable from zero; report binomial intervals and detection-efficiency caveats rather than an uncorrected population rate. Archive a candidate CSV with ICRS, MER/SPE/PHZ IDs, flags, wavelength units, alternative z, cutout links, and independent spectra where present. Check DESI/other optical spectroscopy and HST/DECam imaging coverage before interpreting targets. A single line never establishes secure z. Planck18 distances only for constrained z, propagating its uncertainty.

## Actual outcome / blocker
No verified new MER/SPE catalogue rows, SIR wavelength arrays, tile coverage or independent matched observations were fetched and analysed in this run. The provisional cone cannot be represented as an observed sample; no candidate counts, significance, redshifts, distances, observed image, PDF or discovery are claimed. A literature screen alone does not earn a science/publication day. The existing Fornax, EDF North, NGC 4236, Carousel Lens and nearby-galaxy investigations remain distinct records and were not rerun.

**Next reproducible gate:** retrieve DR1-F SPE-line and MER tables from the IRSA TAP/HATS service, verify coordinate footprint and column units from the current data dictionary, save query and response checksums, then preregister the final fixed footprint *before* inspecting candidate scores. Obtain the SIR FITS arrays and an independent archive coverage response; only then execute and publish a report with observed target images.

## LinkedIn editorial draft — unassigned day; hold for review
Day [number] out of 365 Earthian Days — Can one spectral line tell us how far away a galaxy is?

I checked the new Euclid DR1-Foundation spectral products and prepared a test of how often a single emission-line redshift survives alternative line identifications and independent grism checks. The science test is **not yet run**: I still need verified spectra, catalogue matches and independent archive coverage. No galaxy distance or discovery is being claimed.

Research notes and methods: https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation

You are welcome to write your own scripts, reproduce the archive checks or suggest stronger controls.

#365EarthianDays #AstroNotebooks #OpenScience #Euclid
