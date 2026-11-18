"""Render the compact-double research note from recorded measurements."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle
from xml.sax.saxutils import escape


INK = colors.HexColor("#18232c")
GRAY = colors.HexColor("#4e606c")
TEAL = colors.HexColor("#12566a")
RULE = colors.HexColor("#ccd5da")
STYLES = {
    "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=TEAL, spaceAfter=9),
    "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=30, leading=33, textColor=INK, spaceAfter=12),
    "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=9, leading=13, textColor=GRAY, spaceAfter=17),
    "header": ParagraphStyle("header", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=12, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11.2, leading=15, textColor=INK, spaceAfter=8, alignment=TA_LEFT),
    "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=8.5, leading=11, textColor=GRAY, spaceBefore=6, spaceAfter=8),
    "small": ParagraphStyle("small", fontName="Times-Roman", fontSize=9.7, leading=12.25, textColor=INK, spaceAfter=6),
}


def para(text, style="body"):
    return Paragraph(text, STYLES[style])


def heading(text):
    return para(text, "header")


def table(rows, widths):
    box = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
    box.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.3),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.4),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f3")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7f8")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), .55, RULE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    return box


def plot_cohorts(cohorts, output):
    fig, ax = plt.subplots(figsize=(7.2, 3.2), layout="constrained")
    for key, offset, color, marker in (("pilot", -.012, "#146076", "o"),
                                       ("holdout", .012, "#a24e2e", "s")):
        if key not in cohorts:
            continue
        bins = [b for b in cohorts[key]["bins"] if b["tested"]]
        x = [(b["lo"] + b["hi"]) / 2 + offset for b in bins]
        y = [b["repeat"] / b["tested"] for b in bins]
        lo = [val - b["wilson95"][0] for val, b in zip(y, bins, strict=True)]
        hi = [b["wilson95"][1] - val for val, b in zip(y, bins, strict=True)]
        label = "Pilot" if key == "pilot" else "Held-out fields"
        ax.errorbar(x, y, yerr=[lo, hi], label=label, fmt=marker + "-", lw=1.4,
                    capsize=3, ms=5, color=color)
    from matplotlib.ticker import PercentFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set(xlabel='VIS peak separation (arcsec)', ylabel='Two-peak recurrence in NISP J', ylim=(0, None))
    ax.grid(alpha=.17, axis="y")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output, dpi=190)
    plt.close(fig)


def figure(path, width=None, height=None):
    with PILImage.open(path) as im:
        native_w, native_h = im.size
    if height is None:
        height = width * native_h / native_w
    if width is None:
        width = height * native_w / native_h
    return Image(str(path), width=width, height=height)


def rate(value, total):
    return f"{100*value/total:.2f}%" if total else "unavailable"


def endpoints(values):
    return f"{100*values[0]:.1f} to {100*values[1]:.1f}" if values else "unavailable"


def footer(canvas, doc):
    w, _ = A4
    canvas.setTitle("Subarcsecond peak pairs in Euclid Deep Field North")
    canvas.setStrokeColor(RULE)
    canvas.line(doc.leftMargin, 44, w - doc.rightMargin, 44)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(doc.leftMargin, 29, "EUCLID DR1-FOUNDATION  /  RESEARCH NOTE  /  18 NOVEMBER 2026")
    canvas.drawRightString(w - doc.rightMargin, 29, str(doc.page))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--plate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", type=Path, required=True)
    a = parser.parse_args()
    summary = json.loads((a.results / "cohorts.json").read_text())
    controls = json.loads((a.results / "offset_controls.json").read_text())
    checks = json.loads((a.results / "image_checks.json").read_text())["profiles"]
    audit = json.loads((a.results / "audit.json").read_text())
    pilot, total = (summary[key] for key in ("pilot", "total"))
    groups = [(name, summary[key]) for name, key in (("Pilot", "pilot"), ("Held out", "holdout")) if key in summary]
    holdout = summary.get("holdout")
    plot_cohorts(summary, a.plot)
    area = total["nonoverlapping_common_area_deg2"]
    area_label = f"{area:.3f} deg<super>2</super>" if area is not None else "overlapping fields"
    volume = total["fits_image_range_bytes"] / 1e9
    on_disk = total["two_band_pixel_payload_bytes"] / 1e9
    data = [["Sample", "Tile centres", "Positive VIS", "Inverted VIS", "J repeats / tested", "North shift"]]
    for name, s in groups:
        data.append([name, str(len(s["coverage"])), f"{s['vis_kept_positive']:,}",
                     f"{s['vis_kept_negative']:,}", f"{s['j_repeat']:,} / {s['j_tested']:,}",
                     f"{s['shift_repeat']:,} / {s['shift_tested']:,}"])
    sample_b = (
        f" A subsequent test of {len(holdout['coverage'])} held-out tile centres yielded "
        f"{holdout['j_repeat']:,}/{holdout['j_tested']:,} repeats."
        if holdout else ""
    )
    width = 491
    story = [
        para("RESEARCH NOTE  /  OBSERVED IMAGING", "kicker"),
        para("Subarcsecond peak pairs<br/>in Euclid Deep Field North", "title"),
        para("18 November 2026  |  Working draft for Biswajit Jana", "meta"),
        heading("Abstract"),
        para(
            f"We used a classical peak finder to locate optical doubles in six Euclid DR1-Foundation VIS "
            f"mosaic centres. At the measured sky positions, {pilot['j_repeat']:,} of {pilot['j_tested']:,} "
            f"testable pairs recurred in NISP <i>J</i> ({rate(pilot['j_repeat'], pilot['j_tested'])})."
            + sample_b +
            " Recurrence increased with angular separation. Five of the six brightest near-infrared "
            "repeaters showed a second peak with at least a 10% saddle in a Subaru HSC <i>i2</i> profile. "
            "One of these, EDN-004, has a repeating NISP slitless spectrum feature at 1.31555 micrometres. "
            "Its line identification and the relationship between the two peaks remain open."
        ),
        heading("Data and detection"),
        para(
            "We used the IRSA mirror of the released MER mosaics (Aussel et al. 2026, McCracken et al. "
            "2026, Polenta et al. 2026). The fixed pilot covers the central 6144 by 6144 pixels of tiles "
            "101829775 through 101829780 at 0.1 arcsec per pixel. The held-out list was fixed after the "
            "pilot and before inspection of its images. Both runs used the same thresholds."
        ),
        para(
            "We removed smooth structure with a difference of Gaussians (0.85 and 3.0 pixels in VIS). "
            "Local scores used a median and scaled MAD in 512-pixel cells. We required peaks above 8 and "
            "6 local scores, a 0.38 to 0.95 arcsec separation, a weaker-to-stronger filtered amplitude ratio "
            "of at least 0.25, and a dip of at least 15% of the weaker peak. The selection excludes array "
            "edges, invalid coverage, bright-peak neighbourhoods and close third peaks."
        ),
        para(
            "In <i>J</i>, we used Gaussian widths of 1.25 and 3.5 pixels and a local annular noise estimate. "
            "Two maxima had to lie within 0.16 arcsec of the respective VIS peaks, each above four local "
            "scores, with at least a 10% dip. The preregistered offset shifted both positions 3 arcsec north. "
            "Seven more bearings at the same radius were evaluated after the pilot. The scores describe "
            "filtered contrast in correlated pixel noise."
        ),
        table(data, [69, 62, 79, 79, 110, 92]),
        para(
            "Table 1. The inverted VIS count is a diagnostic of filtered structure, including negative "
            "lobes near real objects. The shift controls sample local chance coincidence around VIS selections.",
            "caption"
        ),
        PageBreak(),
        para("IMAGE SAMPLE", "kicker"),
        para("Recurrence rises with separation", "title"),
        figure(a.plot, width=width),
        para(
            "Figure 1. Fractions in fixed separation intervals. Bars show descriptive Wilson 95% intervals. "
            "The points are offset horizontally for legibility. The stronger sampling unit is the mosaic tile.",
            "caption"
        ),
    ]
    for name, s in groups:
        narrow, wide = s["bins"][0], s["bins"][-1]
        interval = endpoints(s["tile_bootstrap95_wide_minus_narrow"])
        story.append(para(
            f"<b>{name}.</b> Recurrence changed from {narrow['repeat']:,}/{narrow['tested']:,} "
            f"({rate(narrow['repeat'], narrow['tested'])}) at 0.38 to 0.50 arcsec to "
            f"{wide['repeat']:,}/{wide['tested']:,} ({rate(wide['repeat'], wide['tested'])}) at "
            f"0.86 to 0.95 arcsec. Resampling complete tiles gave a 95% interval of {interval} "
            "percentage points for the wide-minus-narrow difference."
        ))
    num_control = sum(c["testable"] for c in controls.values())
    repeat_control = sum(c["shifted_repeats"] for c in controls.values())
    story += [
        para(
            f"Across the eight bearings, {repeat_control} of {num_control:,} testable shifted placements passed. "
            "The placements share the same target list and are correlated. The separation trend persisted in "
            "the pilot across three strata of weaker VIS peak score. Different PSFs, colours and flux ratios "
            "affect recovery. A controlled completeness estimate requires injected sources and empirical PSFs."
        ),
        heading("Coverage and transfer"),
        para(
            f"The {total['paired_tiles']} tile centres contribute {area_label} of common, finite, nonzero "
            f"VIS and <i>J</i> coverage on the native mosaic grid after edge exclusion. FITS WCS corner checks "
            f"test the overlap of cropped footprints. The two image planes contained {on_disk:.2f} GB of "
            f"float32 pixels. The verified FITS row ranges sum to {volume:.2f} GB because each range also "
            "contains pixels outside the cropped columns."
        ),
        para(
            "ESA describes about 1.7 PB for DR1, so a 10% byte target is about 170 TB. IRSA describes an "
            "approximately 1900 square degree DR1 footprint, giving a separate 190 square degree area target. "
            "Both denominators are approximate and depend on the chosen release product set. The present "
            "run covers a small portion of either target."
        ),
        PageBreak(),
        figure(a.plate, height=705),
        PageBreak(),
        para("TARGET AUDIT", "kicker"),
        para("EDN-004 and the single line", "title"),
        para(
            "For the six highest-ranked repeaters we inspected the unfiltered optical and near-infrared "
            "surface brightness along the VIS pair axis and the independently observed Subaru HSC "
            "<i>i2</i> images resampled by MER. The ten associated MER sources carry the catalogue deblend "
            "bit. The Subaru peaks pass the 10% saddle rule in five systems. The coordinate checks found "
            "no ECLIPSE counterpart within 3 arcsec of any of the 658 pilot repeaters. The six top targets "
            "had no close counterpart in the queried SIMBAD, WDS or DESI tables and no containing image "
            "among the HST/JWST footprints returned by the bounded MAST query."
        ),
    ]
    targets = [["Target", "ICRS RA (deg)", "ICRS Dec (deg)", 'VIS sep. (")', "HSC dip"]]
    for target, v in audit.items():
        row = v["candidate"]
        dip = checks[target]["HSC_I2"].get("dip")
        targets.append([target, f"{row['ra']:.6f}", f"{row['dec']:.6f}", f"{row['sep_arcsec']:.3f}",
                        f"{dip*100:.1f}%" if dip is not None else "Unavailable"])
    story.extend([
        table(targets, [78, 108, 105, 93, 107]),
        para("Table 2. Sky coordinates are the midpoint of the VIS pair. The Subaru dip is measured along that axis.", "caption"),
        figure(a.results / "edn004_line.png", width=380),
        para(
            "Figure 2. The brighter VIS component is associated with MER 2718858072642847858. "
            "Points show the unflagged per-bin signal-to-error ratio in the two Euclid grism coadds. "
            "The red coadd lacks the unflagged wavelength coverage required for the formal fit.",
            "caption"
        ),
        para(
            "The blue coadd gives formal S/N 9.58 at 13155.55 Angstrom, or 7.84 after dropping the "
            "brightest bin. Two blue and six red dithers exceed formal S/N 4. Two blue dithers and one "
            "red dither at RGS180 still exceed 4 after the brightest-bin check. The neighbour gives no "
            "individual dither at S/N 4 in this window. The extractors share a crowded slitless scene. "
            "The fitted wavelength came from the Euclid redshift proposal."
        ),
        para(
            "H-alpha at z = 1.0040 agrees with the catalogue photo-z near 1.01 for that component. "
            "[O III] at z = 1.6268 and [O II] at z = 2.5294 place a single line at the same wavelength. "
            "The companion has a catalogue photo-z near 1.40 and weak slitless evidence. Spatially resolved "
            "spectroscopy could test the line identity and the association."
        ),
        PageBreak(),
        para("REPRODUCIBILITY", "kicker"),
        para("Inputs and references", "title"),
        para(
            "The run archive contains the original pilot protocol, the held-out tile list, the Python "
            "scripts, checksummed archive byte ranges, signed detections and rejected seeds, NISP "
            "position controls, registered FITS stamps, and the spectroscopy and catalogue audits. "
            "The six-tile rerun reproduced the candidates, signed table and image summary byte for byte "
            "from the cached archive bytes."
        ),
        heading("Release and instrument papers"),
    ])
    refs = [
        ("Euclid Collaboration, Aussel et al. (2026), Euclid First Data Release 1. Data release overview.", "https://arxiv.org/abs/2611.16510"),
        ("Euclid Collaboration, McCracken et al. (2026), Euclid DR1. VIS processing and data products.", "https://arxiv.org/abs/2611.15890"),
        ("Euclid Collaboration, Polenta et al. (2026), Euclid DR1. Near-infrared processing and data products.", "https://arxiv.org/abs/2611.16119"),
        ("Euclid Collaboration, Corcho-Caballero et al. (2026), Euclid DR1. Colouring Euclid with external ground-based imaging data.", "https://arxiv.org/abs/2611.16533"),
        ("Euclid Collaboration, Lines et al. (2026), ECLIPSE A. Strong lens catalogue overview.", "https://arxiv.org/abs/2611.15883"),
        ("Euclid Collaboration, Le Brun et al. (2026), Euclid DR1. Performance of the redshift measurement and spectroscopic analysis.", "https://arxiv.org/abs/2611.17960"),
    ]
    for title, url in refs:
        story.append(para(f'{escape(title)} <link href="{url}" color="#12566a">{url}</link>', "small"))
    story.append(heading("Archive documentation and comparisons"))
    links = [
        ("ESA / Euclid Consortium, DR1-Foundation Explanatory Supplement", "https://euclid.esac.esa.int/dr/dr1/expsup/"),
        ("IRSA, Euclid DR1 MER image products and cloud access", "https://caltech-ipac.github.io/irsa-tutorials/euclid-cloud-access/"),
        ("Euclid DR1 ECLIPSE object catalogue", "https://doi.org/10.5281/zenodo.19654904"),
        ("Subaru HSC ancillary survey documentation", "https://dawn.ipac.caltech.edu/page/hsc"),
        ("DR1-Foundation publication list", "https://euclid-ec.net/dr1-f-publication/"),
    ]
    for title, url in links:
        story.append(para(f'<link href="{url}" color="#12566a">{escape(title)}</link>', "small"))
    story += [
        heading("Scope and use"),
        para(
            "The sample was selected for the image-domain test. The catalogue and literature checks cover "
            "specific published resources and search radii. Source identities, association and discovery "
            "priority remain unestablished. The text is a working research draft for review and revision "
            "by the researcher."
        ),
        para("Imaging credit ESA/Euclid/Euclid Consortium/NASA and Subaru/WISHES. Data served through IRSA.", "caption"),
    ]
    doc = SimpleDocTemplate(str(a.output), pagesize=A4, leftMargin=52, rightMargin=52,
                            topMargin=59, bottomMargin=58)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
