"""Build the compact, line-number-free Fornax study PDF."""
from pathlib import Path
from io import BytesIO
import argparse
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image as Figure, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

HERE = Path(__file__).resolve().parent
R = HERE/"results"
NAVY = "#10283A"
SLATE = "#405766"
TEAL = "#006F6D"


def build(output):
    fontdir = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont("DejaVu", fontdir/"DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuBold", fontdir/"DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFontFamily("DejaVu",normal="DejaVu",bold="DejaVuBold")
    s = {
        "title": ParagraphStyle("title",fontName="DejaVuBold",fontSize=22,leading=28,textColor=colors.HexColor(NAVY),spaceAfter=8),
        "sub": ParagraphStyle("sub",fontName="DejaVu",fontSize=9.2,leading=13,textColor=colors.HexColor(SLATE),spaceAfter=12),
        "head": ParagraphStyle("head",fontName="DejaVuBold",fontSize=13,leading=17,textColor=colors.HexColor(TEAL),spaceBefore=9,spaceAfter=5),
        "body": ParagraphStyle("body",fontName="DejaVu",fontSize=9.2,leading=13.5,textColor=colors.HexColor(NAVY),spaceAfter=7),
        "cap": ParagraphStyle("cap",fontName="DejaVu",fontSize=8.0,leading=11.5,textColor=colors.HexColor(SLATE),spaceAfter=7),
    }
    def p(txt, key="body"):
        return Paragraph(txt,s[key])
    def image(path, width):
        stream = BytesIO()
        with Image.open(path) as figure:
            h = width*figure.height/figure.width
            figure.convert("RGB").save(stream,format="JPEG",quality=91,optimize=True,subsampling=0)
        stream.seek(0)
        return Figure(stream,width=width,height=h)
    def grid(rows, widths):
        t=Table(rows,colWidths=widths,hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTNAME",(0,0),(-1,0),"DejaVuBold"),("FONTNAME",(0,1),(-1,-1),"DejaVu"),
            ("FONTSIZE",(0,0),(-1,-1),8.3),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#EEF4F6"),colors.white]),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ]))
        return t
    def footer(c, doc):
        c.setStrokeColor(colors.HexColor("#C8D5DC"))
        c.line(42,37,A4[0]-42,37)
        c.setFont("DejaVu",8)
        c.setFillColor(colors.HexColor(SLATE))
        c.drawString(42,23,"Euclid DR1-Foundation  /  Fornax  /  16 November 2026")
        c.drawRightString(A4[0]-42,23,str(doc.page))

    story = [
        p("Faint near-infrared colour outliers<br/>in Euclid Deep Field Fornax","title"),
        p("Biswajit Jana  ·  16 November 2026  ·  DR1-Foundation MER Deep Survey","sub"),
        p("We tested whether faint sources in a published T-dwarf colour box retain those colours in a second Euclid photometric estimator. In a 0.125° radius Fornax field, 28 of 1,413 quality-selected objects at 23 &lt; J ≤ 24 AB entered the box with template-fit fluxes. Thirteen retained nominal aperture colours (46.4%, Wilson 95% interval 29.5–64.2%), and none met the preregistered uncertainty and signal-to-noise criteria. Independent Blanco/DECam and VISTA/VIRCAM observations show sources at the three highest-ranked positions. Their VISTA J−H colours are less blue than the Euclid aperture estimates, with different passbands. Diffraction and a bright halo affect one field. Classifications, redshifts and distances remain unresolved."),
        image(R/"observed_targets.webp",505),
        p("Figure 1. Observed, WCS-registered cutouts, about 24 arcsec wide, north up and east left. The ring marks the MER position. Each panel uses an independent stretch. Native PSFs are retained. F02 lies near bright diffraction and extended halo light.","cap"),
        p("Sample and quality cuts","head"),
        p("The cone was centred at ICRS (52.933°, −28.0885°), geometric area 0.0491 deg². We obtained 3,458 catalogue rows in the J range from the public HATS copy. After detection and near-IR flags and a deblend-parent cut, 2,676 remained. The all-band template-fit S/N ≥ 10 cut left 1,413, including 1,385 comparison sources. No rows merged under the exact-ID and 0.3 arcsec duplicate rule."),
        p("The nominal box was 0.1 &lt; Y−J &lt; 0.9 and J−H &lt; −0.1 (Kiwy et al.). The PSF-matched aperture uses twice the FWHM in diameter. The secure rule required S/N ≥ 5 in each aperture band and a margin ≥ 2 propagated σ from all boundaries. The largest minimum margin was 1.09 σ. Aperture and template-fit fluxes share the Euclid images, and the conditional interval describes this sample without a population completeness correction."),
        PageBreak(),
        p("Catalogue and archive checks","title"),
        image(R/"colour_screen.png",495),
        p("Figure 2. The same template-selected candidates (orange) and J-selected controls in the two Euclid estimators. Axes match. Points outside the displayed ranges remain in the archived quality table.","cap"),
        grid([["ID","ICRS RA, Dec (deg)","Euclid aperture J−H","VIDEO J−H","VIDEO ID"],
          ["F01","53.016973, −28.116720","−0.488 ± 0.313","+0.058 ± 0.093","644247524531"],
          ["F02","52.980603, −28.201983","−0.608 ± 0.297","+0.167 ± 0.147","644248076048"],
          ["F03","52.934558, −28.044552","−0.395 ± 0.360","+0.045 ± 0.109","644247549515"]],[39,146,113,99,107]),
        Spacer(1,6),
        p("VISTA/VIRCAM VIDEO matches lie 0.14–0.43 arcsec from the Euclid positions. The raw colours are descriptive across non-identical passbands. DECam z has 0.262 arcsec native sampling and a broader PSF than Euclid VIS. Local 1.6 arcsec aperture contrasts in the registered z images were 10.29, 6.31 and 9.10, based on nearby blank apertures. Gaia DR3 provided no match within 10 arcsec. CatWISE2020 returned one distant neighbour near F02. VHS DR5 was shallower, and no target catalogue match was found."),
        image(R/"audit/F02/spectrum.png",468),
        p("Figure 3. F02 NISP combined spectra. Coloured points have mask zero. The blue and red products retain 303/335 and 452/523 finite-variance bins, respectively. There is no secure line identification. The grisms are measurements from the same space telescope.","cap"),
        PageBreak(),
        p("Template checks and interpretation","title"),
        image(R/"audit/F03/template_fit.png",505),
        p("Figure 4. F03 as an example of a multimodal galaxy template fit. E and V denote Euclid and VISTA/VIRCAM bands. Points show catalogue fluxes and their errors, with a separate 5% floor used in the fit. The dashed line is the pipeline galaxy PHZ median.","cap"),
        grid([["ID","PHZ median","Best galaxy z","Descriptive galaxy profile spans"],
          ["F01","0.52","0.00 (grid edge)","0.00–0.06"],
          ["F02","2.69","1.12","1.00–1.18"],
          ["F03","0.63","1.24","0.12–0.20, 0.26–0.94, 1.18–1.38"]],[43,85,124,252]),
        Spacer(1,6),
        p("The exploratory fit integrated published Euclid and VIRCAM response curves, with Galactic E(B−V) = 0.0073 and separate survey normalizations. On identical near-IR bands, the tested mid-T standards had χ² of about 47, 91 and 79, compared with about 13, 9 and 5 for the best alternatives. The flagged F02 VIDEO Z value had no suitable local upper limit and was excluded. The galaxy spans show grid points within Δχ² = 4 of each galaxy-family minimum. They provide a model sensitivity check rather than calibrated uncertainty."),
        p("VLT/VIMOS VANDELS DR4 and GOODS contained no target matches within 1 arcsec and no matched positive-redshift control in the J-selected cone. No distance is derived. The adopted reference cosmology for later secure galaxy redshifts is Astropy Planck18."),
        p("Data and reproduction","head"),
        p('The <link href="https://github.com/Biswajit1999/daily-astro-notebooks/tree/research/euclid-dr1-foundation-day01-20261114/euclid-dr1-foundation/fornax-faint-infrared-outliers" color="#006F6D">study record</link> gives the frozen protocol, Python scripts, candidate register, full quality table, FITS cutouts, spectrum masks, archive IDs and checksums. The public MER HATS mirror supplied the production data after the IRSA TAP request timed out.'),
        p('Euclid Collaboration, Aussel et al. (2026), DR1 release overview. IRSA products 675 (MER Deep Survey), 683 (MER mosaics) and 680 (SIR 1D). Kiwy et al. (2026), AJ 171, 108. ESO VISTA VIDEO DR5, DOI 10.18727/archive/58. Legacy Imaging Surveys DR10. The study record lists all citations and product identifiers.',"cap"),
        p("This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA). The VISTA photometry was obtained from the ESO Science Archive Facility.","cap"),
    ]
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=35,bottomMargin=49,
                          author="Biswajit Jana",title="Faint near-infrared colour outliers in Euclid Deep Field Fornax")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=HERE/"Euclid_Fornax_Colour_Outliers.pdf")
    build(parser.parse_args().output)
