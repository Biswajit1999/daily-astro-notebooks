# Hunting unresolved binaries in the solar neighborhood with Gaia's RUWE

I pulled a real sample of 12,000 bright (G < 12), nearby (parallax > 10 mas, so within 100 pc) Gaia
DR3 stars with good parallax signal-to-noise, and looked at two astrometric diagnostics that can hint
at an unresolved binary companion without ever resolving it: RUWE (renormalised unit weight error,
which should sit close to 1.0 for a clean single-star astrometric fit) and astrometric excess noise
significance (how confidently the extra scatter in a star's position measurements exceeds what its
formal errors predict).

Using the conventional RUWE > 1.4 cut, 3,140 stars (26.2%) came out as binary candidates. Using
astrometric excess noise significance > 2, a striking 11,951 stars (99.6%) came out flagged. That huge
gap surprised me at first, but it makes sense once I thought about it: this is a bright, high-precision
sample, so the formal position errors are tiny, and even a small amount of real excess scatter (crowding,
faint contamination, genuine low-amplitude wobble) clears a 2-sigma significance threshold easily. Every
single RUWE-flagged star also passed the excess-noise test, so RUWE > 1.4 looks like the much more
conservative, more specific cut of the two for this kind of bright, nearby sample, while the excess-noise
significance test is basically saturated and not very useful for discriminating between stars here.

I built a results table (a cross-tab of the two flags) and a couple of diagnostic plots — a RUWE
histogram with the 1.4 cut marked, and a colour-magnitude diagram coloured by the RUWE flag. The
overall agreement rate between the two diagnostics (both true or both false) is only 26.6%, driven
almost entirely by the excess-noise test being so lenient here.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
