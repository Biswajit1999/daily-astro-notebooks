**Author:** Biswajit Jana  
**Date:** January 2, 2026

# A from-scratch BPT line-ratio classifier, validated against SDSS's own pipeline labels

SDSS's own spectroscopic pipeline assigns each galaxy spectrum a `subclass` such as `STARFORMING`,
`STARBURST`, or `AGN`, derived internally from its own emission-line analysis. I wanted to check how well a
simple, independent, from-scratch classifier could recover that real label using only the published physics
rather than trusting the pipeline blindly. I queried real emission-line fluxes (`H-alpha`, `H-beta`,
`[O III] 5007`, `[N II] 6584`, all with S/N > 5) and the real pipeline `subclass` for two independent live
samples -- 110 pipeline-labeled star-forming/starburst galaxies and 90 pipeline-labeled AGN, 200 galaxies
total -- and classified each one purely from its line ratios using the Kewley et al. (2001) theoretical
maximum-starburst line on the BPT diagram, with no reference at all to the pipeline label during
classification.

The from-scratch classifier agrees with SDSS's own real pipeline label for 93% of the sample (186/200),
with AGN precision/recall and SF precision/recall both reported directly from `sklearn.metrics` in the
notebook. The disagreements cluster tightly around the Kewley dividing line itself on the BPT diagram --
exactly where a binary line-ratio cut is most sensitive to flux measurement noise, and where the SDSS
pipeline's own classification likely draws on additional information (e.g. broad-line detection) that this
simple two-ratio rule does not use. That a two-line-ratio rule taken straight from a 25-year-old theoretical
paper reproduces the pipeline's real classification this well is genuine, independent validation of both the
Kewley line itself and of the pipeline's internal consistency.

## What's next

A natural extension is to add the Kauffmann (2003) line for a genuine three-way SF/Composite/AGN
classification (the binary split used here is the correct comparison against a two-class pipeline label, but
throws away the composite population entirely), and to rerun at S/N > 3 and S/N > 10 cuts to quantify how
classifier accuracy degrades or improves with line-flux data quality.

## Data source and citation

- SDSS DR18 SkyServer SQL search: https://skyserver.sdss.org/dr18/
- MPA-JHU `galSpecLine` value-added catalog: https://wwwmpa.mpa-garching.mpg.de/SDSS/DR7/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
- Baldwin, Phillips & Terlevich (1981), PASP 93, 5: https://doi.org/10.1086/130766
- Kewley et al. (2001), ApJ 556, 121: https://doi.org/10.1086/321545
- Kauffmann et al. (2003), MNRAS 346, 1055: https://doi.org/10.1111/j.1365-2966.2003.07154.x
