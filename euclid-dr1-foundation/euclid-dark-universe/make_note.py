"""Render the day-one observational note and its figures."""
from pathlib import Path
import argparse
from io import BytesIO
import json
from xml.sax.saxutils import escape

from PIL import Image as Raster
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle


rl_config.useA85=0
FONT_DIR=Path("/usr/share/fonts/truetype/dejavu")
SANS,SANS_BOLD,SERIF,SERIF_BOLD=("Helvetica","Helvetica-Bold","Times-Roman","Times-Bold")
if all((FONT_DIR/f"{n}.ttf").exists() for n in ("DejaVuSans","DejaVuSans-Bold","DejaVuSerif","DejaVuSerif-Bold")):
    SANS,SANS_BOLD,SERIF,SERIF_BOLD=("DejaVuSans","DejaVuSans-Bold","DejaVuSerif","DejaVuSerif-Bold")
    for face in (SANS,SANS_BOLD,SERIF,SERIF_BOLD):
        pdfmetrics.registerFont(TTFont(face,str(FONT_DIR/f"{face}.ttf")))
INK=colors.HexColor("#171717")
DARK=colors.HexColor("#232323")
MUTE=colors.HexColor("#505050")
LINE=colors.HexColor("#cdcdcd")
STYLES={
    "k":ParagraphStyle("section",fontName=SANS_BOLD,fontSize=9,leading=12,spaceAfter=10,textColor=DARK),
    "title":ParagraphStyle("title",fontName=SERIF_BOLD,fontSize=27,leading=30,spaceAfter=13,textColor=INK),
    "body":ParagraphStyle("body",fontName=SERIF,fontSize=10.5,leading=15,spaceAfter=9,textColor=INK),
    "head":ParagraphStyle("head",fontName=SANS_BOLD,fontSize=10.7,leading=14,spaceBefore=9,spaceAfter=5,textColor=DARK),
    "caption":ParagraphStyle("caption",fontName=SANS,fontSize=8.3,leading=11,spaceBefore=7,spaceAfter=9,textColor=MUTE),
    "ref":ParagraphStyle("ref",fontName=SERIF,fontSize=9.4,leading=12,spaceAfter=7,textColor=INK),
}


def p(s,style="body"):
    return Paragraph(s,STYLES[style])


def image(path,width=484):
    with Raster.open(path) as data:
        height=data.height*width/data.width
        if path.name=="Abell3128_RGB.png":
            preview=data.convert("RGB")
            preview.thumbnail((1400,1500),Raster.Resampling.LANCZOS)
            buffer=BytesIO()
            preview.save(buffer,format="JPEG",quality=92,optimize=True,subsampling=0)
            buffer.seek(0)
            return Image(buffer,width=width,height=height)
    return Image(str(path),width=width,height=height)


def table(matrix,widths):
    t=Table(matrix,colWidths=widths,hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONT",(0,0),(-1,0),SANS_BOLD,8.1),
        ("FONT",(0,1),(-1,-1),SANS,8.35),
        ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#ebebeb")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f6f6f6")]),
        ("LINEBELOW",(0,0),(-1,0),.5,LINE),
        ("TEXTCOLOR",(0,0),(-1,0),DARK),
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),
    ]))
    return t


def footer(canvas,document):
    w,_=A4
    canvas.setAuthor("Biswajit Jana")
    canvas.setTitle("Projected mass and cosmic acceleration with public observations")
    canvas.setStrokeColor(LINE)
    canvas.line(53,44,w-53,44)
    canvas.setFont(SANS,7.7)
    canvas.setFillColor(MUTE)
    canvas.drawString(53,29,"EUCLID DR1-FOUNDATION + DESI DR2  /  RESEARCH NOTE  /  18 NOVEMBER 2026")
    canvas.drawRightString(w-53,29,str(document.page))


def ref(text,url):
    return p(f'{escape(text)} <link href="{url}" color="#242424">{escape(url)}</link>',"ref")


def run(root,dest):
    arc=json.loads((root/"arc_geometry.json").read_text())
    mass=json.loads((root/"lens_budget.json").read_text())
    bao=json.loads((root/"bao_fits.json").read_text())
    sensitive=json.loads((root/"robustness.json").read_text())
    arc_check=sensitive["arc"]["band_results"]["VIS"]
    stellar=sensitive["stellar"]
    cosmic=sensitive["bao"]
    range_vis=arc_check["median_range_arcsec"]
    range_mass=arc_check["one_plane_mass_range_msun"]
    measurements=bao["full"]
    band=arc["per_band"]
    near=arc["foreground_counterfactual"]
    far=arc["cluster_redshift_geometry"]
    s=[
        p("RESEARCH NOTE  /  OBSERVED IMAGES AND DISTANCES","k"),
        p("Projected mass and<br/>cosmic acceleration","title"),
        p("Biswajit Jana  |  18 November 2026  |  Research draft","caption"),
        p("Aim","head"),
        p("Use released images and independent spectroscopy to measure a lensing mass scale in a projected cluster field. "
          "Test whether a conservative lensing estimate can exceed the fitted stellar budget in the public lens catalogue. "
          "Use an independent BAO distance sample to test whether the expansion history favours present acceleration."),
        image(root/"Abell3128_Observed_Arc.png"),
        p("Figure 1. The 22 arcsec panels are made from real Euclid DR1-Foundation and Blanco DECam FITS cutouts. "
          "The blue arc's optical ridge is measured in ten sectors centred at position angles 175 to 220 degrees east of north.","caption"),
        p("Cluster projection test","head"),
        p("ESA's A3128 image includes a background cluster, DES J0330-5228 (ACT-CL J0330-5227). "
          "XMM-Newton Fe K spectroscopy and Magellan optical data put that cluster near z = 0.44 (Werner et al. 2007). "
          "Gemini/GMOS spectroscopy gives the Southwest arc z = 1.4541 (Nord et al. 2016). "
          "We start from the published DES centre and use azimuthal background subtraction in each band."),
        table([["Band","Ridge sectors","Median (arcsec)","Sector range (arcsec)"]]+
              [[label,str(v["sectors"]),f'{v["median_arcsec"]:.2f}',
                f'{v["sector_range_arcsec"][0]:.2f} to {v["sector_range_arcsec"][1]:.2f}']
               for label,key in [("Euclid VIS","VIS"),("DECam g","DES-G"),("DECam i","DES-I")] for v in [band[key]]],
              [110,94,135,148]),
        PageBreak(),
        p("OBSERVED THREE-BAND COMPOSITE","k"),
        p("The gravitational arc in RGB","title"),
        image(root/"Abell3128_RGB.png",width=455),
        p("Figure 2. Red is Euclid NISP H, green is Euclid VIS, and blue is Blanco DECam g. The common 0.1 arcsec grid was checked at the four corners and image centre. Each channel was sky-subtracted and placed on AB zero point 30. Display gains (R, G, B) = (0.60, 2.15, 8.00), followed by a shared asinh intensity stretch, show structure across the different bands.","caption"),
        p("The image retains each band's point-spread function. Use the calibrated FITS planes with PSF matching for a quantitative colour measurement. The report's radius measurements use the individual mosaics.","caption"),
        PageBreak(),
        p("STRONG LENSING  /  PROJECTED MASS","k"),
        p("Deflector redshift and inferred mass","title"),
        p(f"The {band['VIS']['median_arcsec']:.2f} arcsec VIS ridge agrees with the published DES Einstein-radius proxy "
          "of 6.1 ± 1.5 arcsec. The DECam g ridge is 6.22 arcsec. The broader DECam i range records band-dependent "
          "ridge ambiguity. The range across sectors describes morphology and extraction sensitivity."),
        p("Treating the VIS radius as an Einstein-radius proxy gives M = (c<super>2</super> / 4G) "
          "(D<sub>l</sub>D<sub>s</sub> / D<sub>ls</sub>) theta<super>2</super> in a circular one-plane model. "
          "Distances use the Planck18 reference cosmology. The foreground row below keeps the observed arc and moves "
          "the nominal deflector to the foreground redshift as a geometric control."),
        table([["Assumed deflector","Redshift","Aperture radius","Mass (trillion solar masses)"],
               ["Background cluster",f'{far["z_deflector"]:.3f}',f'{far["radius_kpc"]:.1f} kpc',f'{far["arc_proxy_mass_msun"]/1e12:.2f}'],
               ["Abell 3128 control",f'{near["z_deflector"]:.3f}',f'{near["radius_kpc"]:.1f} kpc',f'{near["arc_proxy_mass_msun"]/1e12:.2f}']],
              [151,71,99,166]),
        p(f"The redshift assignment changes the mass proxy by a factor of {arc['mass_ratio_background_to_foreground']:.2f}. "
          "The VIS sector values span around 7.9 to 11.2 trillion solar masses at z = 0.44. "
          "The resulting proxy is sensitive to the mass profile and structure along the sightline. It estimates "
          "total projected gravitating mass in the assumed geometry. A two-plane lens model would be needed for "
          "a separate foreground contribution."),
        p("Extraction and redshift sensitivity","head"),
        p(f"The {arc_check['usable']} VIS settings vary the centre by up to 0.25 arcsec, the angular background window, the radial smoothing (0.05-0.20 arcsec), and whether edge sectors are included. Their median radii span {range_vis[0]:.2f}-{range_vis[1]:.2f} arcsec. Repeating the one-plane mass conversion over z = 0.42-0.46 gives {range_mass[0]/1e12:.2f}-{range_mass[1]/1e12:.2f} trillion solar masses. These are sensitivity bounds over selected settings. The grid reuses the same photons."),
        p("Independent checks","head"),
        p("The published X-ray spectrum identifies the redshift of the gas component. Earlier DECam weak-lensing "
          "tomography independently found a background mass contribution. The image comparison here uses Euclid "
          "and DES imaging, with published X-ray and optical spectroscopy for redshifts."),
        ref("Werner et al. 2007. Complex X-ray morphology of Abell 3128.","https://arxiv.org/abs/0708.3253"),
        ref("Nord et al. 2016. Spectroscopic confirmation of DES strong lenses.","https://arxiv.org/abs/1512.03062"),
        ref("McCleary et al. 2015. Mass substructure in Abell 3128.","https://arxiv.org/abs/1503.02823"),
        PageBreak(),
        p("STRONG LENSING  /  STELLAR MASS","k"),
        p("A conservative stellar-budget check","title"),
        p(f"We joined the two released ECLIPSE tables by lens ID and retained {mass['n_catalogue_lenses']:,} "
          "expert Grade A systems with successful inspected models, accepted stellar fits, defined radii and redshifts, "
          "and without disc or large-system warnings. In flat geometry D<sub>s</sub>/D<sub>ls</sub> exceeds one. "
          "Setting it to one gives a conservative geometric mass proxy for each circularized model radius. "
          "We compare this aperture proxy to the catalogue's total fitted stellar mass, which includes remnants."),
        image(root/"Lens_Stellar_Budget.png"),
        p("Figure 3. The comparison uses the lower fitted radius and photometric redshift and upper fitted stellar mass. "
          "Dashed lines mark equality and the extra +0.30 dex stellar-mass allowance. Gravity, light and sightline matter each affect the interpretation.","caption"),
        table([["Comparison","Systems above stellar budget","Systems tested"],
               ["Catalogue central values",str(mass["central_estimate_above_stars"]),"2,161"],
               ["Lower radius and z, upper stellar mass",str(mass["lower_radius_lower_z_upper_stars"]),"2,161"],
               ["Same bounds and +0.30 dex stellar mass",str(mass["lower_radius_lower_z_upper_stars_plus_0p30dex"]),"2,161"],
               ["DESI-redshift overlap with +0.30 dex allowance",str(mass["specz_subset_above_stars_plus_0p30dex"]),str(mass["specz_subset"])]],
              [250,142,95]),
        p(f"In an illustrative joint stress test, use a uniform external convergence of 0.10, lowering the attributed lens mass proxy by 10%, and allow gas equal to 25% of the enlarged stellar budget. {stellar['joint_stress_at_0p30dex']} systems clear both allowances. The gas and convergence inputs are assumed values. The 30-system DESI overlap contains zero of the 26 photometric-redshift excesses at +0.30 dex. Those candidates therefore still need spectroscopic validation."),
        PageBreak(),
        p("COSMIC EXPANSION  /  DESI DR2 BAO","k"),
        p("BAO fits with and without acceleration","title"),
        p("We fitted the 13 published galaxy and Lyman-alpha BAO distances with their full 13 × 13 covariance. "
          "For each late-time FLRW history we profiled the ruler factor c/(H<sub>0</sub>r<sub>d</sub>) analytically. "
          "The shape test therefore uses a common scale left free in every fit."),
        image(root/"DESI_BAO_Expansion.png"),
        p("Figure 4. Each point is a prediction minus the observed BAO distance in units of its reported marginal error. "
          "The numerical fit uses the full covariance, including the correlated transverse and radial distances.","caption"),
    ]
    labels={"flat_lambda":"Flat Lambda-CDM","curved_lambda":"Curved Lambda-CDM",
            "curved_nonaccelerating_lambda":"Curved Lambda-CDM with q0 ≥ 0",
            "matter_and_curvature_only":"Matter + curvature, no Lambda"}
    rows=[["History","Matter density","q0","Minimum chi-square"]]
    for key,label in labels.items():
        v=measurements[key]
        rows.append([label,f'{v["omega_m"]:.3f}',f'{0. if abs(v["q0"])<1e-8 else v["q0"]:.3f}',f'{v["chi2"]:.2f}'])
    flat=measurements["flat_lambda"]
    lo,hi=flat["q0_profile_68"]
    s += [
        table(rows,[230,83,66,108]),
        p(f"In flat Lambda-CDM, q0 = {flat['q0']:.3f} with a delta-chi-square = 1 range of {lo:.3f} to {hi:.3f}. "
          "The best curved fit also accelerates. Restricting the curved model to q0 ≥ 0 raises chi-square "
          "from 9.95 to 173.28. Removing the two Lyman-alpha distances still gives 9.87 versus 111.00. "
          "These comparisons apply to the tested FLRW histories and leave the physical cause of acceleration open."),
        PageBreak(),
        p("COSMIC EXPANSION  /  SENSITIVITY","k"),
        p("Curvature and redshift leverage","title"),
        p("For curved Lambda-CDM, q0 = 1.5 Omega_m + Omega_k - 1. At each fixed q0 we minimize chi-square over matter density and the common BAO ruler scale, with curvature set by that equation. We retain non-negative matter and Lambda densities and expanding histories over the redshift span."),
        image(root/"DESI_BAO_Robustness.png"),
        p("Figure 5. Left, profile chi-square relative to its minimum. The dashed levels are 1 and 3.84. Right, best-fit q0 after removing all distances at one redshift and refitting with the corresponding covariance submatrix.","caption"),
        table([["Curved Lambda-CDM result","q0 / range"],
               ["Full sample, minimum",f'{cosmic["q0_curved"]:.3f}'],
               ["Profile delta chi-square = 1",f'{cosmic["profile_ranges"]["delta1"][0]:.3f} to {cosmic["profile_ranges"]["delta1"][1]:.3f}'],
               ["Profile delta chi-square = 3.84",f'{cosmic["profile_ranges"]["delta3p84"][0]:.3f} to {cosmic["profile_ranges"]["delta3p84"][1]:.3f}'],
               ["Omit each redshift group in turn",f'{cosmic["leave_one_q0_range"][0]:.3f} to {cosmic["leave_one_q0_range"][1]:.3f}']],
              [290,197]),
        p(f"Across the seven omissions, the non-acceleration constraint raises chi-square by {cosmic['leave_one_delta_range'][0]:.1f} to {cosmic['leave_one_delta_range'][1]:.1f}. The profile ranges condition on the curved Lambda-CDM model and the published BAO covariance. They quantify present acceleration within that model family."),
        PageBreak(),
        p("DATA AND REPRODUCIBILITY","k"),
        p("Measurements and sources","title"),
        p("The image test processes four FITS cutouts of 491 by 491 pixels from Euclid MER tile 102017310. "
          "The archive manifest records the original FITS byte ranges, object versions and SHA-256 hashes. "
          "The catalogue calculation reads 15,072 published ECLIPSE physical-property rows. The main "
          "distance fit uses the published compressed DESI vector and covariance."),
        p("Euclid and DESI roles","head"),
        p("The Euclid image and published lens models supply the two lensing tests. The DESI fit uses an "
          "independent data set and does not estimate an equation of state from Euclid. The DR1-Foundation "
          "release contains imaging, spectra and catalogues. The Euclid team schedules shear and higher-level "
          "clustering and weak-lensing products for DR1 Complete."),
        p("Inputs","head"),
        ref("Aussel et al. 2026. Euclid DR1 release overview.","https://arxiv.org/abs/2611.16510"),
        ref("ESA/Euclid Consortium. DR1-Foundation Explanatory Supplement.","https://euclid.esac.esa.int/dr/dr1/expsup/"),
        ref("ESA. Euclid image of the Abell 3128 field.","https://www.esa.int/ga/media/about-us/directorates/science/euclid/euclid-s-view-of-rich-galaxy-cluster-abell-3128"),
        ref("Lines et al., Nightingale et al., Nersesian et al. 2026. ECLIPSE catalogue, lens models and stellar estimates.","https://doi.org/10.5281/zenodo.19654904"),
        ref("DESI Collaboration. Published DR2 BAO and cosmology results.","https://data.desi.lbl.gov/doc/papers/dr2/"),
        ref("DESI Collaboration. DR2 BAO measurements and cosmological constraints.","https://arxiv.org/abs/2503.14738"),
        p("The notebook reruns the arc extraction, lens-budget summaries and BAO models. The companion "
          "archive contains the inputs, source scripts, provenance and machine-readable results. "
          "ECLIPSE catalogue construction used several candidate-selection methods, including machine learning "
          "and expert grading. This analysis uses the released catalogue and classical calculations."),
    ]
    SimpleDocTemplate(str(dest),pagesize=A4,leftMargin=53,rightMargin=53,
                      topMargin=57,bottomMargin=58).build(s,onFirstPage=footer,onLaterPages=footer)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results",type=Path)
    parser.add_argument("pdf",type=Path)
    args=parser.parse_args()
    run(args.results,args.pdf)
