# HST M87 preview field-placement audit

**Question:** Can the selected HST preview support morphology or jet claims when M87 lies at the frame boundary?

This executed scientific audit reports provenance, uncertainty or robustness, reusable outputs, and explicit claim limits.

![Main evidence](m87_preview_boundary_audit.png)

I worked with a real MAST HST WFC3 preview (`id5o27qbq_raw.jpg`, 4206x2070 pixels) containing the M87 galaxy. The original audit already established something important and honest: M87's light reaches the bottom frame boundary at every threshold I tested (up to 12.5% of the bottom edge is bright), so I explicitly rejected any morphology or jet-shape claim from this preview — the target is cropped, not fully framed.

On top of that boundary audit, I added a real radial brightness profile computed outward from the brightest pixel within the target crop, plus a horizontal cross-section through it (`m87_radial_profile.png` / `.csv`), and a zoomed cutout of that brightest sub-region as its own labelled figure (`m87_zoom_cutout.png`). The brightest point in the analyzed crop sits at pixel (577, 452) within a 1177x518-pixel sub-frame, and the radial profile peaks about 6.4 pixels out from there — consistent with a compact bright nucleus close to, but not exactly centered on, the crop.

The results table (`m87_summary_table.csv`) again records frame size and brightest-pixel location as real measurements, while explicitly marking pixel scale and angular size as "not available" — this display JPEG has no WCS, and I could not reliably retrieve a calibrated, target-centered FITS product in this environment. The honest constraint from the original audit (frame truncation) still stands and is the main limitation on any further quantitative claim here.

[Open the executed notebook](notebook.ipynb) · [Machine-readable result](result.json)
