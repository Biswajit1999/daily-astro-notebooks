# Subarcsecond peak pairs in Euclid Deep Field North

18 November 2026. Euclid DR1-Foundation, VIS and NISP J MER mosaics, with Subaru WISHES HSC i2 comparison imagery.

| Cohort | Paired tile centres | VIS positives | J repeats / testable | North shifts passed / testable |
| --- | ---: | ---: | ---: | ---: |
| Fixed pilot | 6 | 5,495 | 658 / 5,314 | 0 / 5,309 |
| Held-out fields | 12 | 10,438 | 1,135 / 10,062 | 0 / 10,075 |

The original pilot replay produced identical candidates, signed pairs and summary files from the verified cached FITS crops. One of 42,494 testable placements passed across eight pilot offset directions. The holdout recurrence rises from 10/1,498 (0.67%) below 0.50 arcsec to 435/2,032 (21.41%) at 0.86–0.95 arcsec. The tile-bootstrap interval for that difference is 19.2–22.1 percentage points. The two-band coverage is 0.502917 deg², using disjoint WCS crop footprints and counting common finite nonzero pixels inside the edge margin. The verified row ranges sum to 9,024,307,200 bytes. The two-band arrays analysed contain 5,435,817,984 bytes of float32 pixels.

The strongest follow-up case is EDN-004 at ICRS midpoint (271.885434°, +64.284832°). A feature at 1.31555 µm repeats in the NISP slitless measurements of MER source 2718858072642847858. The blue coadd gives formal S/N 9.58, or 7.84 after dropping the brightest bin. Individual blue and red dithers support the feature while the red coadd does not meet the clean-coverage cut. The line identification and physical association remain unresolved. See the observing note for the competing interpretations and the external catalogue checks.

The [held-out colour follow-up](HOLDOUT_COLOUR.md) measures a persistent optical–infrared brightness reversal in NCH-042 across three visits. Both components have public MER entries. The pair’s physical nature remains unresolved.

The [ten-target follow-up series](results/candidate_series/) applies the same aperture and visit tests to the next ten pairs in the fixed ranking. It includes calibrated FITS stamps, per-target measurements and a comparative report.

## Extended research notebook

[Euclid_DR1F_Colab.ipynb](Euclid_DR1F_Colab.ipynb) is a 25-cell research notebook credited to Biswajit Jana. It computes the matched separation contrast, derives the detector response with empirical J-band injections, and refits the EDN-004 spectra by grism orientation. The validation inputs and results are described in [VALIDATION.md](VALIDATION.md).

## Rerun the image analysis

Run from this study directory on Python 3.12 with curl available. A session processing several large tiles needs a few GB of memory and scratch space. Use fewer workers to reduce memory and network load.

```bash
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
python search_doubles.py --cache work/pilot-cache --output work/pilot --workers 3
python fetch_holdout.py work/holdout-cache --workers 4
python search_doubles.py --cache work/holdout-cache --output work/holdout --workers 3 \
    --tiles 101829781 101829782 101830399 101830400 101830401 101830402 \
            101830403 101830404 101830405 101830406 101830407 101830408
python offset_controls.py --candidates work/pilot/candidates.csv \
    --cache work/pilot-cache --output work/pilot --workers 3
python cohort_summary.py --pilot work/pilot --pilot-cache work/pilot-cache \
    --holdout work/holdout --holdout-cache work/holdout-cache --output work/cohorts.json
```

`vet.py` registers the top six pilot cutouts and performs the initial archive checks. `catalogue.py`, `archive_crossmatches.py`, `secondary.py`, and `image_flags.py` inspect pipeline catalogue entries, other archives, and image flags. `spectra.py` and `edn004_dithers.py` extract the SIR coadds and inspect the individual dither spectra. `photometry.py` runs the exploratory template fits. The [report](Euclid_DR1F_Compact_Pairs_Report.pdf) and [image plate](Euclid_DR1F_Observed_Pairs.png) can be regenerated with `target_plate.py` and `make_report.py`. The complete run bundle includes the signed positive and negative seed tables, candidate lists, FITS stamps, spectra, archive queries, and a Colab notebook.

## Scaling the image search

The unit of work is one tile centre, or a small shard of tile IDs. For a larger sample, record one manifest per shard, including failed products and input range checksums. Merge on ICRS position with explicit ownership of overlap regions. Compute the area union from the observed common-band footprint. This run's 6144-pixel centre crops intentionally leave gaps and cannot be counted as complete tiles. Use a separate validated full-mosaic pass with overlap masks for contiguous area coverage. Keep the image metric, survey area and all-product archive bytes separate.

IRSA reports a footprint of about 1,900 deg². Ten percent of that footprint is about 190 deg². The ESA supplement quotes about 1.7 PB for the full DR1 archive, which gives a separate target of about 170 TB. Colab can run individual image shards. The large-area survey should run against the cloud-hosted mosaics or close to the source data on ESA Datalabs.

## Data references

- Euclid Data Release 1 overview and data processing. [Aussel et al. 2026](https://arxiv.org/abs/2611.16510) · [McCracken et al. 2026](https://arxiv.org/abs/2611.15890) · [Polenta et al. 2026](https://arxiv.org/abs/2611.16119)
- MER mosaics, ancillary images and cloud access. [IRSA archive](https://caltech-ipac.github.io/irsa-tutorials/euclid-cloud-access/) · [Corcho-Caballero et al. 2026](https://arxiv.org/abs/2611.16533)
- Cross-check catalogue. [ECLIPSE, Lines et al. 2026](https://arxiv.org/abs/2611.15883) · [Catalogue DOI](https://doi.org/10.5281/zenodo.19654904)
- ESA release details and hosted analysis. [DR1-Foundation supplement](https://euclid.esac.esa.int/dr/dr1/expsup/) · [ESA Datalabs](https://euclid.esac.esa.int/dr/dr1/expsup/Ch16.S1.html)
