# Checking a quasar's redshift from its SDSS spectrum

I picked a spectroscopically confirmed SDSS quasar (SDSS J000006.53+003055.2) and tried to recover its
redshift by hand, using just the position of one strong emission line, then compared that to the redshift
SDSS's own pipeline reports.

Redshift is how much a distant object's light has been stretched toward redder wavelengths by the
expansion of the universe — bigger redshift generally means farther away and further back in time. Quasars
are useful for this because their spectra have very strong, broad emission lines that are easy to spot even
at low signal-to-noise.

I used the MgII line (2798 Angstrom in the quasar's own rest frame) as my marker: I predicted where it
should land in the observed spectrum using the pipeline's redshift, then searched for the actual flux peak
near that prediction and worked the redshift back out from where the peak really was.

My single-line estimate came out close to the pipeline's value, which was satisfying — the pipeline is more
precise because it fits many lines simultaneously with proper line templates, but a single strong line gets
you most of the way there. It's a nice illustration of how much information is packed into just one
emission line's wavelength shift.
