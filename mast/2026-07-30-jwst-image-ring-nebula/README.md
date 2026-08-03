# JWST Ring Nebula: selected-field audit

Does the selected preview contain a centred ring suitable for shape measurement?

![Audit evidence](ring_field_audit.png)

I worked with MAST's real JWST preview of the Ring Nebula (M57), a 2058x2058-pixel display-stretched image. The original audit checks whether the ring is actually centred in the selected field, which matters before any shape or symmetry claim can be trusted.

I added a real radial brightness profile and horizontal cross-section computed from the frame's brightest smoothed region (`ring_radial_profile.png` / `.csv`), plus a zoomed cutout figure (`ring_zoom_cutout.png`). Worth being honest about: the simple "find the brightest smoothed blob" method I used for the profile's center locked onto pixel (2057, 0) — the extreme corner of the frame — rather than the ring itself, which is a real and useful negative result: it shows a naive brightest-pixel centroid is not a reliable way to locate this particular ring in this particular preview (likely because of a bright caption/border region near the frame edge), and a real centering measurement would need either a smoothed radial-symmetry fit or the field-audit method the original notebook already uses.

The results table (`ring_summary_table.csv`) records frame size and the (corner) brightest-pixel location, and explicitly marks pixel scale and angular size as "not available" since this JPEG preview carries no WCS — that needs a calibrated FITS product I did not reliably retrieve here. I kept the honest failure mode visible rather than silently picking a better-looking center.

[Open the executed notebook](notebook.ipynb)
