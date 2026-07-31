# Measuring the exoplanet radius valley from the NASA Exoplanet Archive

This notebook downloads the current confirmed transiting-planet composite
table, applies explicit period/radius/precision cuts, locates the radius valley
with a kernel-density estimate, bootstraps its uncertainty, and measures a
coarse period dependence.

It validates the result against the published radius-valley range while
explaining why an uncorrected confirmed-planet catalogue cannot distinguish
competing atmospheric-loss mechanisms.

[Open the notebook](notebook.ipynb)
