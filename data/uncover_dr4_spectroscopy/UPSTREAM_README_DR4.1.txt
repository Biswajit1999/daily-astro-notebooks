UNCOVER First Abell 2744 NIRSpec/PRISM observations, catalogs, and data products
Authors: Sedona Price, Rachel Bezanson, Ivo Labbe, Jenny Greene, Wren Suess, David Setton

Release: 4.1
Internal Spectroscopic Version: 0.8
Strong Lensing Model Version: 2.0
Created: 25 June 2024
Last Updated: 5 Dec 2024

If you use these catalogs, please cite the corresponding papers:
Price et al. 2024 (https://ui.adsabs.harvard.edu/abs/2024arXiv240803920P/abstract), 
Bezanson et al. 2024 (https://ui.adsabs.harvard.edu/abs/2022arXiv221204026B/abstract). 

Additionally, if you use the lensing magnification catalog, please also cite: 
Furtak et al. 2023 (https://ui.adsabs.harvard.edu/abs/2023MNRAS.523.4568F/abstract)


** Updates **

2024-12-05 / DR4.1:
    This release now includes an additional flag in the redshift catalog indicating potential background subtraction issues.
    A catalog listing the shutter locations (collating information from the previously released ancillary files into a more 
    convenient format) has also been added. 
2024-08-07: Release updates

AVAILABLE FILES
---------------

├── README_DR4.1_spec.txt :: this file
│
├── catalogs
│   ├── uncover-msa-default_drz-DR4.1-zspec.[dat/fits] :: zspec catalog, with quality flags  (see columns below)
│   ├── uncover-msa-default_drz-DR4-lines.[dat/fits] :: line fluxes from msaexp, UNCORRECTED FOR LENSING MAGNIFICATION (see columns below)
│   ├── uncover-msa-DR4-zspec-magnifications.[dat/fits] :: lensing magnifications for the targets using the v2.0 SL model (see columns below)
│   └── uncover-msa-DR4.1-shutter-location.[dat/fits] :: shutter locations for all targets/masks (see columns below)
│       
├── spectra
│   ├── default_drz
│   │   ├── uncover_DR4_prism-clear_2561_[ID_MSA].spec.fits :: Reduced object spectrum (1D/2D/profiles; see "File extensions / entries")
│   │   │
│   │   ├── uncover_DR4_prism-clear_2561_[ID_MSA].flam.png :: Plot of spectrum (1D/2D/trace), in flam (10^-20 erg/s/cm^2/Angstrom)
│   │   ├── uncover_DR4_prism-clear_2561_[ID_MSA].fnu :: Plot of spectrum (1D/2D/trace), in fnu (uJy)
│   │   ├── uncover_DR4_prism-clear_[ID_MSA].d2d.png :: Figure showing msaexp drizzled combined arrays
│   │   │
│   │   └── uncover_DR4_[ID_MSA].extract.log :: msaexp slit combination/extraction log file
│   │
│   └── phot_cal
│       └── default_drz
│           ├── uncover_DR4_prism-clear_2561_[ID_MSA].spec.cal.fits :: Object spectrum, with 1D flux calibration using 0.32" diameter aperture phot 
│           └── uncover_DR4_prism-clear_2561_[ID_MSA].spec.cal.png :: Overview of polynomial flux calibration
│
├── redshift_fits
│   └── default_drz
│       ├── uncover_DR4_prism-clear_2561_[ID_MSA].spec.zfit.fits :: msaexp best-fit model
│       ├── uncover_DR4_prism-clear_2561_[ID_MSA].yaml :: msaexp best fit model information (see "File extensions / entries") 
│       ├── uncover_DR4_prism-clear_2561_[ID_MSA].zfit.yaml :: msaexp coarse and refined redshift/chi2 grids (see "File extensions / entries")
│       │
│       ├── uncover_DR4_prism-clear_2561_[ID_MSA].chi2.png :: msaexp best fit model chi2 plot
│       ├── uncover_DR4_prism-clear_2561_[ID_MSA].zfit.png :: msaexp best fit plot of spec + best fit model
│       │
│       └── uncover_DR4_prism-clear_2561_[ID_MSA].zfit.log :: msaexp best fit log
│
│
└── ancillary :: Ancillary mask and intermediate data products
    └──mask_metadata :: DS9 region and fits files containing information about masks and targets



RECOMMENDED USE & OVERVIEW
--------------------------

We recommend only using spectroscopic redshifts with flag_zspec_qual=3 or 2 ("secure" or "solid" redshifts; see Price et al. 2024). 


The DR4 catalog contains flags detailing what features present in each spectrum, based on visual inspection: 
    "flag_emission_lines" (two or more emission lines); 
    "flag_line_and_break" (a continuum break/stellar bump and one emission line); 
    "flag_break_strong_abs_features_only" (only continuum break(s) and strong absorption features); 
    "flag_break_only" (only a continuum break); 
    "flag_stellar_bump_only" (only a stellar bump).
where in each case, =1 is in the category, =0 is not within the category


A flag of whether a spectrum was successfully observed & reduced for each target (flag_successful_spectrum, with =1 does have a spectrum, =0 has no spectrum) is also included.


This release includes a lineflux catalog, derived during the msaexp redshift fits. We note this process is automated, and sometimes based on template-only fits. The precision and uncertainties of lines should be carefully examined before use. 
*** NOTE THE LINE FLUXES ARE NOT CORRECTED FOR LENSING MAGNIFICATION ***


We recommend using the *default* spectra, eg "spectra/default_drz/uncover_DR4_prism-clear_2561_[ID_MSA].spec.fits", for analysis. 


For spectra with a median S/N > 1, "phot_cal" spectra are also available, with fits with a linear polynomial to match to the SED within a 0.32" diameter aperture using the DR3 UNCOVER photometry. However, these corrections are *extrapolations* towards the blue/red ends of the spectra. Thus we recommend using the standard spectra for analysis, and only using the phot_cal spectra for, eg, co-plotting spectra and photometry. 



--------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------



REDSHIFT CATALOG FORMAT:  (uncover-msa-full_depth-default_drz-DR4-zspec.[dat/fits])
------------------------
id_msa :: object identification number for MSA design
ra/dec :: targeted object centroid position in world frame 

z_spec :: spectroscopic redshift (minimum chi2 from best msaexp fits; described above)
z_spec16 :: spectroscopic redshift 16th percentile (from full range msaexp fits; described above)
z_spec50 :: spectroscopic redshift 50th percentile (from full range msaexp fits; described above)
z_spec84 :: spectroscopic redshift 84th percentile (from full range msaexp fits; described above)

flag_zspec_qual :: Redshift fit quality flag. (=3 for secure; =2 for solid; =1 for suspect, =0 very poor/missing)
flag_successful_spectrum :: Spectrum success flag. =1 for a successful spectrum; =0 for missing/unreducable spectrum

flag_potential_local_background_issue :: Advisory local background subtraction issue flag. (1 = objects with 
potential issues from galaxy/ICL light in the neighboring shutters, 0 = no local background subtraction issues). 
*** Note, this is only an advisory flag to alert users to inspect the 2D spectrum and evaluate if this background issue could impact their planned analysis. ***

flag_emission_lines :: Category flag for two or more emission lines (=1 for in the category, =0 for not in)
flag_line_and_break :: Category flag for a continuum break/stellar bump and one emission line (=1 for in the category, =0 for not in)
flag_break_strong_abs_features_only :: Category flag for only continuum break(s) and strong absorption features (=1 for in the category, =0 for not in)
flag_break_only :: Category flag for only a continuum break (=1 for in the category, =0 for not in)
flag_stellar_bump_only :: Category flag for only a stellar bump (=1 for in the category, =0 for not in)

method_best_zfit :: Fit method adopted for the best-fit redshift and linefluxes (described below)
method_zuncert :: Fit method adopted for determining redshift uncertainties (described below)


texp_tot :: Total exposure time (hr)
masks :: comma-separated string listing mask numbers on which the object was included

id_DR3 :: ID of the source in public DR3 catalog (all within < 0.24" radius)
sep_DR3 :: radius in arcsec to the public DR3 catalog match 




MSAEXP LINE FLUX CATALOG FORMAT:  (uncover-msa-full_depth-default_drz-DR4-lines.[dat/fits])
--------------------------------
id_msa :: object identification number for MSA design
z_spec :: spectroscopic redshift (minimum chi2 from msaexp fits; described above)


f_X :: line flux, msaexp best model (1e-20 erg/s/cm2)
e_X :: uncertainty on line flux, msaexp best model (1e-20 erg/s/cm2)
eqw_X :: line equivalent width, msaexp best model

    Notes:
    ~~~~~~
    
    Lines are sorted by restframe wavelength
    
    Full set of line wavelengths/definitions can be found in msaexp. 
    
    Common lines / doublets are noted without a RF wavelength, including: 
    Lyman alpha, Balmer (Ha, Hb, Hg, Hd), 
    Paschen (PaA, PaB, PaG, PaD, Pa8, Pa9, Pa10), 
    Brackett (BrA, BrB, BrG, BrD), Pfund (PfB, PfG, PfD, PfE). 

    Lines with RF wavelength < 1um have wavelengths denoted in *Angstroms*.
    Lines with RF wavelength >1um, <3um have wavelengths denoted in *Nanometers* (i.e., HeI-1083 at 10833Angstrom)
    Lines with RF wavelength >3um have wavelengths denoted in *Microns* (i.e., PAH features)





STRONG LENSING MAGNIFICATIONS CATALOG FORMAT:  (uncover-msa-DR4-zspec-magnifications.txt)
---------------------------------------------

id_msa :: object identification number for MSA design

mu :: magnification (best-fit; = 1 for foreground objects and objects without spec-zs)
mu_low_68, mu_high_68, mu_low_95, mu_high_95 :: magnification posterior percentiles (for uncertainty)

mu_rad :: Radial magnification (best-fit; = 1 for foreground objects and objects without spec-zs)
mu_rad_low_68, mu_rad_high_68, mu_rad_low_95, mu_rad_high_95 :: Radial magnification posterior percentiles (for uncertainty)

mu_t :: Radial magnification (best-fit; = 1 for foreground objects and objects without spec-zs)
mu_t_low_68, mu_t_high_68, mu_t_low_95, mu_t_high_95 :: Tangential magnification posterior percentiles (for uncertainty)

gamma1 :: Shear gamma1 (best-fit; = 1 for foreground objects and objects without spec-zs)
gamma1_low_68, gamma1_high_68, gamma1_low_95, gamma1_high_95 :: Shear gamma1 posterior percentiles

gamma2 :: Shear gamma2 (best-fit; = 1 for foreground objects and objects without spec-zs)
gamma2_low_68, gamma2_high_68, gamma2_low_95, gamma2_high_95 :: Shear gamma2 posterior percentiles 

theta :: Lensing rotation angle (degrees, best-fit; = 0 for foreground objects and objects without spec-zs)
theta_low_68, theta_high_68, theta_low_95, theta_high_95 :: Lensing rotation angle posterior percentiles


    Notes:
    ~~~~~~
    These target magnifications are computed using the best-fit target zspec reported in the zspec catalog (see above). 
    All objects with no spec-z or that are foreground objects (z<0.3) have mu = 1.







SHUTTER LOCATIONS CATALOG:  (uncover-msa-DR4-shutter-location.[dat/fits])
--------------------------

id_msa :: object identification number for MSA design

mask_num :: mask number 

SRC_SHUT_S_REGION_1 :: string containing the RA/Dec coordinates of the shutter corners for the source shutter (center of the 3 shutter slit)

SHUT_S_REGION_0/2 :: string containing the RA/Dec coordinates of the shutter corners for the flanking shutters (outsides of the 3 shutter slit)

metafile :: Mask metadata filename containing this information (see ancillary/mask_metadata/)





FILE EXTENSIONS / ENTRIES:
--------------------------

uncover_DR4_prism-clear_2561_[ID_MSA].spec.fits :: reduced spectra
  Extensions:
    1 : SPEC1D     :: 1D spectrum, binary table. Header includes extraction profile parameters (see msaexp)

        wave :: wavelength, in um
        flux :: flux, in uJy
        err  :: flux uncertainty, in uJy
        sky  :: sky, in uJy
        path_corr :: pathloss correction factor (already multiplied in flux, err, sky)  (unitless)
        npix :: Number of pixels in 1D bin
	norm_corr :: normalization correction factor (unitless)
	flux_sum :: Summed flux in y range
	profile_sum :: Sum of profile
	var_sum :: Sum of variance

    2 : SCI        :: 2D spectrum image, in uJy
    3 : WHT        :: 2D weight image, in 1/uJy^2
    4 : PROFILE    :: 2D profile image
    5 : PROF1D     :: 1D profile, binary table (see msaexp)

	pix :: pixel number
	profile :: observed trace profile
	pfit :: fitted profile

    6 : BACKGROUND :: 2D background image
    7 : SLITS      :: Slit information for each exposure, binary table (see msaexp)


uncover_DR4_prism-clear_2561_[ID_MSA].spec.zfit.fits :: msaexp best-fit model
  Extensions:
    1 : SPEC1D
        wave :: wavelength, in um
        flux :: flux, in uJy
        err  :: flux uncertainty, in uJy
        sky  :: sky, in uJy
        path_corr :: pathloss correction factor (already multiplied in flux, err, sky)  (unitless)
        npix :: Number of pixels in 1D bin
	norm_corr :: normalization correction factor (unitless)
	flux_sum :: Summed flux in y range
	profile_sum :: Sum of profile
	var_sum :: Sum of variance
        corr :: Flux scaling
        escale :: Extra scaling of uncertainties
        full_err :: Full uncertainty, including "sys_err" added in quadrature
        valid :: Mask of valid data
        R :: Spectral resolution
        to_flam :: conversion factor to 1e-20 erg/s/cm2/AA
        model :: Total SED model 
        mline :: Line model



uncover_DR4_prism-clear_2561_[ID_MSA].yaml :: msaexp best fit model information
  Key dictionary entries:
    z :: Best-fit (minimum chi2) redshift

  (see msaexp software+docs for full entry list)
  

uncover_DR4_prism-clear_2561_[ID_MSA].zfit.yaml :: msaexp coarse and refined redshift/chi2 grids
  Key dictionary entries:
    zg0  :: Coarse redshift grid
    chi0 :: Chisq over zg0
    zg1  :: Refined redshift grid
    chi1 :: Chisq over zg1

  (see  msaexp software+docs for full entry list)

  Note msaexp determines zbest = zg1[np.argmin(chi1), 
  and we compute the 16/50/84th percentiles using zg0 & chi0. 




--------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------------



REDUCTION DETAILS:
------------------

The files used in this reduction are available from: https://dx.doi.org/10.17909/8k5c-xr27

The spectra are reduced using:
  msaexp (v0.8.5)  (https://github.com/gbrammer/msaexp)
  grizli (v1.11.9) (https://github.com/gbrammer/grizli)
  snowblind (v0.2.1) (https://github.com/mpi-astronomy/snowblind)
  and the STScI jwst pipeline (v1.14.0) (https://jwst-docs.stsci.edu/jwst-science-calibration-pipeline) 

The jwst_1241.pmap reference files were used.


Reduction steps are as follows:

  Uncalibrated frames that have been preprocessed by the jwst pipeline are downloaded from MAST

  Run stage 1 jwst pipeline up through the end of the "jump" step. 
  Run snowblind to identify and correct "snowballs" 
  Run remaining stage 1 jwst pipeline steps

  Run msaexp steps: additional iteration snowball masking, 1/f noise correction, remove median bias of each exposure with RNOISE rescaling
  Run stage 2 jwst pipeline steps to assign WCS, flag open microshutters, extract 2D slits, apply slit-level flat-fielding, apply bar shadow corrections, apply photometric calibration

  Perform local background subtraction using background from neighboring microshutters
  Rectify 2D spectra (with all wavelength bins fully independent)
  Drizzle combine all exposures for a target, with drizzle settings of pixel fraction and wavelength sampling = 1
   
  Extract 1D spectra from 2D local background-subtracted spectra using optimal extraction. 
  Compute path-loss corrections based on target fitted spatial profile width and predicted intra-shutter position. 





REDSHIFT MEASUREMENTS & LINE FLUXES:
------------------------------------

Initial redshift fits for all targets are performed with msaexp using the EAZY "corr_sfhz_13" templates within the range z=[0.05, 14] (the "template" fits).
A second fit using lines and splines (the "lines+splines" fit) is the repeated within +-0.03(1+z) of the template best-fit redshift 
(or z=[0.05, 14] if the template fit failed). 

The reported redshift fit for each object is determined as follows: 

* First, the redshift is adopted in order of preference:

(1) For targets that only have continuum features based on visual inspection (ie, only break/stellar bumps, and possibly with absorption lines), 
    the "template" redshift fit is adopted as the "best-fit" and used for the redshift uncertainties. 

(2) For all other targets not flagged as only having continuum features during visual inspection, if at least one line is detected at S/N >= 3 in 
    the "lines+splines" fit, then the "lines+splines" fit is adopted as the "best-fit". The "template" fit is used to derive the redshift uncertainties 
    (given the restricted redshift fit range on the "lines+splines"); if the template fit fails, the redshift uncertainties are determined from the 
    "lines+splines" fit also. 

(3) For all other targets not flagged as only having continuum features during visual inspection *and* without any lines detected at S/N >=3 
    in the "lines+splines" fit, then the "template" fit is adopted as the "best-fit", and used the redshift uncertainties.


* However, for a subset of galaxies identified during visual inspection, we manually refit the redshifts and use these fits instead in 
the zspec/lines catalogs (eg, to handle break confusion; incorrect initial z ranges from templates despite multiple robust emission lines). 

* Finally, we manually set the redshift of the 3 observed brown dwarfs (zspec=0).



The linefluxes in the line catalog are taken from the best-fit msaexp redshift solution fit (as described above). 


The zspec catalog contains entries that describe what fit was adopted for the zspec/lines best-fit ("method_best_zfit") and 
zspec uncertainties ("method_zuncert"). 
Here "templ" or "spl+lines" denotes the initial automated fits; "manual/templ" or "manual/spl+lines" denotes manual refits 
using msaexp fits with templates or lines+splines; "fixed" denotes manually fixed values (e.g., the 3 brown dwarfs at zspec=0)





