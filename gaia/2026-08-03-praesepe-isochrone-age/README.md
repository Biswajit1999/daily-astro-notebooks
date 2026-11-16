**Author:** Biswajit Jana  
**Date:** June 27, 2026

# Praesepe (M44): a turnoff age from real Gaia DR3 data

I pulled a real Gaia DR3 sample around Praesepe (M44), the open cluster also called the Beehive,
using a 1.3 degree cone search centered on its known position plus cuts on parallax (4.8-6.0 mas),
proper motion, parallax signal-to-noise, and RUWE (Gaia's astrometric fit-quality diagnostic). That
gave 549 raw candidates, and after an additional cut on the BP/RP photometric excess factor to reject
blended or contaminated photometry, 540 members survived. Their median parallax puts the cluster at
185 pc, close to the commonly cited ~186 pc distance.

I built a colour-magnitude diagram from real Gaia photometry (BP-RP colour vs. absolute G magnitude,
using each star's own parallax for the distance modulus) and located the main-sequence turnoff — the
point where the sequence bends because the most massive members have started evolving away from it.
I found it at BP-RP ~ 0.23, absolute G ~ -0.08. Converting that to a mass with a standard
mass-luminosity scaling (L proportional to M^3.5) and then to an age with the standard main-sequence
lifetime relation (t ~ 10 Gyr x M^-2.5) gave an estimated turnoff mass of 3.6 solar masses and an age
of about 400 Myr.

That's noticeably younger than the commonly cited literature range for Praesepe of roughly 590-800
Myr, so my estimate falls outside it. I think that's a real limitation of the method rather than a
data problem: this simple analytic scaling doesn't account for stellar evolution properly near the
turnoff, where luminosity changes fast for a small age change, and a couple of photometric outliers in
the turnoff zone can shift the answer by a lot. A full isochrone-grid fit (PARSEC, MIST) would be the
correct next step rather than trusting this back-of-envelope number.

[Open the executed notebook](notebook.ipynb)

**Citation:** Gaia DR3 (`gaiadr3.gaia_source`), ESA Gaia mission. https://www.cosmos.esa.int/web/gaia-users/credits
