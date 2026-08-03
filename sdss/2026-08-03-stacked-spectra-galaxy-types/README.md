# Three real SDSS galaxies, overlaid: AGN vs. star-forming vs. quiescent

I wanted to put three real, different galaxy types on the same rest-frame, continuum-normalized axis and
compare their line strengths directly rather than describing them separately. I reused the three targets from
my other two SDSS notebooks this week: NGC 5875 (SDSS `AGN` classification, z = 0.01170, S/N = 30.3), NGC 4047
(`STARFORMING`, z = 0.01144, S/N = 43.4), and NGC 7647 (passive elliptical, z = 0.04108, S/N = 47.3).

After de-redshifting each spectrum and dividing by a 101-pixel median-filter continuum, I overlaid all three
on one plot from 3700-7000 A rest frame. The differences are immediate and large: the AGN and star-forming
spectra both spike well above the continuum at H-alpha, H-beta, and the forbidden lines, while the elliptical
sits essentially flat except for real absorption dips.

I quantified this instead of just eyeballing it: measuring H-alpha equivalent width gives -28.9 A (strong
emission) for the AGN, -3.7 A for the star-forming galaxy, and +1.1 A (absorption) for the elliptical --
exactly the expected ordering and sign flip. H-beta gave a genuinely interesting surprise: in the star-forming
galaxy it came out net *positive* (+1.55 A, i.e. absorption-dominated), even though this is a star-forming
galaxy that should show Balmer emission. Looking directly at the normalized spectrum explains it: there's a
real stellar Balmer absorption trough (down to ~0.87) with only a weak nebular emission bump (up to ~1.05) on
top of it, so the net line comes out absorption-dominated. This is the real, well-known Balmer "emission
infill" effect where young ionized gas's emission line sits inside the same fiber's underlying stellar
absorption line, and for the weaker H-beta transition the two can be comparable in strength.

## What's next

I would add a fourth, BPT-composite galaxy to see if its H-alpha EW sits between the star-forming and AGN
cases, replace the crude local-extremum EW measurement with a real Gaussian (stellar-absorption + nebular-
emission) two-component fit, and stack many galaxies per class rather than one fiber per class to get a real
median composite spectrum.

## Data source and citation

- SDSS DR18 spectra: https://skyserver.sdss.org/dr18/
- SDSS-IV citation: https://www.sdss.org/collaboration/citing-sdss/
