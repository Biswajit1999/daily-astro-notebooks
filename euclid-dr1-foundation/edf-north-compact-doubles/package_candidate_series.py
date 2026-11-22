"""Write the per-source evidence packets and the comparative research report."""
from argparse import ArgumentParser
import gzip
import io
import json
from pathlib import Path

from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from candidate_series import TOKENS, write
from holdout_colours import BANDS, PIXEL
from measure_holdout_colours import RADII, components
from plot_holdout_lead import COLOURS, TITLES, central_view, draw_band, rgb, stretch

FOOTPRINT = 81
ORDER = ("VIS","J","H")
PRESENT = (*ORDER,"i2")


def cutout(data, t, band, meta, path):
    middle = data.shape[0]//2
    half = FOOTPRINT//2
    arr = data[middle-half:middle+half+1,middle-half:middle+half+1]
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN","DEC--TAN"]
    w.wcs.crval = [t["ra"],t["dec"]]
    w.wcs.crpix = [(FOOTPRINT+1)/2]*2
    w.wcs.cdelt = [-PIXEL/3600,PIXEL/3600]
    w.wcs.radesys = "ICRS"
    h = w.to_header()
    h["SCOUTID"] = t["candidate"]
    h["BAND"] = band
    h["TILE"] = t["tile"]
    h["BUNIT"] = meta["unit"]
    if meta.get("magzero") is not None:
        h["MAGZERO"] = meta["magzero"]
    h["RA_A"] = t["ra1"]
    h["DEC_A"] = t["dec1"]
    h["RA_B"] = t["ra2"]
    h["DEC_B"] = t["dec2"]
    h["HISTFILE"] = "target.json"
    with io.BytesIO() as out:
        fits.PrimaryHDU(data=np.asarray(arr,dtype=np.float32),header=h).writeto(out,checksum=True)
        path.write_bytes(gzip.compress(out.getvalue(),mtime=0))


def aperture_mag(bands,band,radius="0.28"):
    return bands.get(band,{}).get(radius,{}).get("b_minus_a_aperture_mag")


def visited(visit):
    complete = sum(all(all(str(radius) in obs[b].get("apertures",{}) for radius in RADII)
                       for b in TOKENS) for obs in visit["visits"].values())
    return complete, len(visit["passing_visits"])


def display_visits(ax, visits):
    for band in ORDER:
        times, med, low, high = [], [], [], []
        for visit in visits.values():
            entry = visit[band]
            ap = entry.get("apertures",{})
            base = ap.get("0.28",{}).get("b_minus_a_aperture_mag")
            mags = [m["b_minus_a_aperture_mag"] for m in ap.values() if m["b_minus_a_aperture_mag"] is not None]
            if base is None or not mags:
                continue
            times.append(Time(entry["mjd"],format="mjd").to_datetime())
            med.append(base)
            low.append(base-min(mags))
            high.append(max(mags)-base)
        if times:
            ax.errorbar(times,med,yerr=[low,high],capsize=2,marker="o",markersize=3.,
                        color=COLOURS[band],label=band,linewidth=1.)
    ax.axhline(0,color=".55",linewidth=.8)
    ax.set_title("Separate Euclid visits",loc="left",fontsize=10,weight="bold")
    ax.set_ylabel("B minus A aperture mag")
    ax.spines[["top","right"]].set_visible(False)
    locator = mdates.AutoDateLocator(minticks=2,maxticks=4)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.tick_params(labelsize=7)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=7,frameon=False,ncol=3,loc="best")


def figure(path, target, cube, meta, phot, visits):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})
    fig, axes = plt.subplots(2,3,figsize=(10.2,6.9))
    fig.subplots_adjust(left=.08,right=.955,top=.83,bottom=.145,wspace=.32,hspace=.28)
    label = target["candidate"]
    fig.text(.08,.955,f"{label} · Compact-pair colour and visit checks",weight="bold",size=16,color="#24373e")
    fig.text(.08,.907,f"Euclid Deep Field North  ·  {target['ra']:.6f}°, {target['dec']:+.6f}°  ·  "
             f"{target['sep_arcsec']:.3f}″ between VIS peaks",size=10,color="#465960")
    points = components(target)
    for ax,band in zip(axes.flat,PRESENT):
        if band in cube:
            draw_band(ax,stretch(central_view(cube[band])),TITLES[band],points)
        else:
            ax.set_axis_off()
            ax.set_title(f"{band} mosaic unavailable")
    if all(b in cube for b in ORDER):
        draw_band(axes[1,1],rgb(cube,meta,phot["psf_metadata"]),"Euclid false-colour",points)
    else:
        axes[1,1].set_axis_off()
    display_visits(axes[1,2],visits["visits"])
    axes[0,0].plot([-.95,.05],[-1.19,-1.19],color="white",lw=1.)
    axes[0,0].text(-.45,-1.08,"1″",ha="center",color="white",size=7)
    fig.text(.08,.081,"North up, east left. The false-colour panel maps H/J/VIS to red/green/blue at approximate common resolution.",
             size=8,color="#465960")
    fig.text(.08,.054,"Visit bars span aperture radii. Negative B − A means B is brighter. Individual image stretches differ.",
             size=8,color="#465960")
    fig.text(.08,.026,"Biswajit Jana  ·  ESA / Euclid / Euclid Consortium / NASA IRSA and Subaru WISHES imaging",
             size=8,color="#465960")
    fig.savefig(path,dpi=130)
    plt.close(fig)


def fmt(val):
    return "unavailable" if val is None else f"{val:+.3f}"


def euclid_peaks(rows):
    nearest = []
    for i in range(2):
        if not rows:
            nearest.append(None)
            continue
        row = min(rows,key=lambda r:r["peak_offsets_arcsec"][i])
        nearest.append(row if row["peak_offsets_arcsec"][i]<=.25 else None)
    return nearest


def note(root,t,phot,visit,catalogue):
    label=t["candidate"]
    good_total, passes = visited(visit)
    ext=catalogue["external"]
    by_band={b:aperture_mag(phot["bands"],b) for b in BANDS}
    pretty = {True:"passes",False:"does not pass"}
    matches=euclid_peaks(catalogue["euclid"]["MER"].get("rows",[]))
    match_info=[r["OBJECT_ID"] if r else None for r in matches]
    rank_zero=[r for r in catalogue["euclid"]["SPE"].get("rows",[])
               if r.get("hdu")=="SPE_GALAXY_CANDIDATES" and r.get("SPE_RANK")==0 and r["OBJECT_ID"] in match_info]
    success=int(sum((r.get("SPE_Z_PROB") or 0)>.99 and (r.get("SPE_Z_REL") or 0)>.05 for r in rank_zero))
    res = [
        f"# {label}", "", "Biswajit Jana · Euclid Deep Field North", "",
        f"The VIS peaks are separated by {t['sep_arcsec']:.3f}″ at "
        f"ICRS {t['ra']:.7f}°, {t['dec']:+.7f}°. The pair ranked {t['programme_rank']} in the fixed filter-score search.",
        "", "[Image and visit plot](figure.png) · [Native and matched aperture results](photometry.json) · "
        "[Visit measurements](visits.json) · [Catalogue outputs](crossmatches.json) · [FITS inputs](target.json)",
        "", "| Band | B − A aperture magnitude at 0.28″ |", "|---|---:|",
    ]
    res.extend(f"| {b} | {fmt(val)} |" for b,val in by_band.items())
    res.extend(["", f"The primary VIS–J–H reversal **{pretty[phot['three_band_rank_reversal']]}** in the native mosaics. "
                f"It **{pretty[phot['smoothed_reversal']]}** across the two approximate Gaussian PSF settings. "
                f"The Subaru i2 check **{pretty[phot['subaru_optical_order']]}** the expected optical order. "
                f"{passes} of {good_total} complete visit checks pass at all aperture radii.",
                "", "### Catalogue and classification checks", ""])
    for i,r in enumerate(matches):
        name="AB"[i]
        if r is None:
            res.append(f"- Peak {name} has no MER centroid within 0.25″ in this tile's extracted table."
                       if "rows" in catalogue["euclid"]["MER"] else "- The MER table could not be tested for this peak.")
        else:
            res.append(f"- Peak {name} matches MER ID {r['OBJECT_ID']} at {r['peak_offsets_arcsec'][i]:.3f}″.")
    for k in ("gaia","simbad","desi"):
        r=ext[k]
        res.append(f"- {k.upper()} returned {len(r['rows'])} matches inside the search radius."
                   if "rows" in r else f"- {k.upper()} returned an error recorded in the query output.")
    res.extend([f"- The nearest published ECLIPSE entry is {t['nearest_eclipse_arcsec']:.1f}″ away.",
                f"- {success} of {len(rank_zero)} rank-zero SPE galaxy redshift proposals clear the illustrative IRSA cuts. "
                "A proposal alone cannot establish the redshift of each component in a close blend.",
                "", "The measurements leave the physical class open.",
                "", "[Series methods and comparative results](../README.md)", ""])
    (root/"README.md").write_text("\n".join(res))
    return {"rank":t["programme_rank"],"label":label,"separation_arcsec":t["sep_arcsec"],
            "native_reversal":phot["three_band_rank_reversal"],"matched_reversal":phot["smoothed_reversal"],
            "subaru_order":phot["subaru_optical_order"],"passing_visits":passes,"complete_visits":good_total,
            "component_mer_ids":match_info,"spe_proposals_passing_example_cut":success,"aperture_magnitudes":by_band}


def report(root,meta,rows):
    write(root/"summary.json",rows)
    stable=[r for r in rows if r["matched_reversal"] and r["native_reversal"] and r["passing_visits"]>=2]
    independent=[r for r in stable if r["subaru_order"]]
    lines = [
        "# Ten additional compact-pair investigations in Euclid Deep Field North", "",
        "**Biswajit Jana** · 22 November 2026", "",
        f"Ten pairs at ranks {rows[0]['rank']}–{rows[-1]['rank']} were drawn from the {meta['eligible_reversals']} reversals "
        f"in the fixed filter-score screen of {meta['parent_pairs']:,} held-out image pairs. "
        "These ranks were outside the twelve measured in the previous report.", "",
        f"{sum(r['native_reversal'] for r in rows)} of 10 pass the three-band native-aperture check. "
        f"{len(stable)} pass both the approximate PSF-matching check and at least two separate visits. "
        f"{len(independent)} of those also pass the independent Subaru i2 aperture-order test.", "",
        "| Target | Separation | Native reversal | PSF-matched reversal | Subaru optical order | Passing / complete visits |",
        "|---|---:|---|---|---|---:|",
    ]
    for r in rows:
        label=r["label"]
        vals=["yes" if r[k] else "no" for k in ("native_reversal","matched_reversal","subaru_order")]
        lines.append(f"| [{label}]({label}/) | {r['separation_arcsec']:.3f}″ | {' | '.join(vals)} | "
                     f"{r['passing_visits']}/{r['complete_visits']} |")
    fence=chr(96)*3
    lines.extend(["", "## Methods and scope", "",
        "- Reuse the published input positions and the earlier fixed ranking procedure. Remove the previously measured 12. "
        "Require no ECLIPSE entry within 3″ for inclusion. The selection concerns colour reversal.",
        "- Register calibrated VIS, J, H and Subaru i2 mosaics to a 0.1″ north-up grid. The 81 × 81 FITS stamps preserve "
        "the central registered pixels and celestial axes. Photometry and its sky tests use the larger archive cutouts.",
        "- Apply 0.20″, 0.28″ and 0.35″ apertures and the sky-difference test. All radii must preserve the expected "
        "VIS/J/H signs by more than five times a local background-difference scatter. This excludes blending and model uncertainty.",
        "- Repeat after approximate Gaussian PSF matching at 0.65″ and 0.80″ using Euclid tile PSF headers. "
        "Select the first, middle, and last common VIS/J/H observation IDs and repeat the signed measurements at the fixed centroids.",
        "- Check Gaia DR3, SIMBAD and DESI DR1 at each midpoint. Extract Euclid MER, PHZ and SPE rows using per-tile FITS files "
        "and associate a centroid to a VIS peak within 0.25″. Both components may contaminate each other's apertures or spectra.",
        "- A stable image pair is a candidate for physical interpretation. These cuts establish brightness ordering in the images.", "",
        "## Reproduce", "", "Install the shared [requirements](../../requirements.txt) and run from the study directory.", "",
        fence+"bash", "python candidate_series.py --cache work/new-candidates",
        "python package_candidate_series.py --cache work/new-candidates --output work/series-packets", fence, "",
        "This work has made use of the Data Release (DR1) data from the Euclid mission of the European Space Agency (ESA). "
        "The measurements use IRSA-hosted calibrated Euclid and Subaru WISHES imagery. "
        "[Euclid release and data DOI](https://irsa.ipac.caltech.edu/data/Euclid/docs/overview_dr1.html) · "
        "[ECLIPSE catalogue](https://doi.org/10.5281/zenodo.19654904) · "
        "[IRSA spectroscopy example](https://caltech-ipac.github.io/irsa-tutorials/euclid-intro-phz-catalog/)", "",
        "ChatGPT assisted with archive queries, code, and figure preparation.", ""])
    (root/"README.md").write_text("\n".join(lines))


def main(cache,output):
    data = {s:json.loads((cache/f"series_{s}.json").read_text())
            for s in ("selection","photometry","visits","catalogues")}
    sel = data["selection"]
    shared = {k:v for k,v in sel.items() if k not in ("mosaics","candidates")}
    output.mkdir(parents=True,exist_ok=True)
    findings = []
    for t in sel["candidates"]:
        name = t["candidate"]
        root = output/name
        root.mkdir(exist_ok=True)
        mosaic = sel["mosaics"][name]
        phot, visit, catalogue = (data[k][name] for k in ("photometry","visits","catalogues"))
        write(root/"target.json",{**t,"selection":shared,"mosaics":mosaic})
        with np.load(cache/f"{name}.npz") as cube:
            for band in PRESENT:
                if band in cube:
                    cutout(cube[band],t,band,mosaic[band],root/f"{band}.fits.gz")
                else:
                    write(root/f"{band}_unavailable.json",mosaic[band])
            figure(root/"figure.png",t,cube,mosaic,phot,visit)
        for key,value in (("photometry",phot),("visits",visit),("crossmatches",catalogue)):
            write(root/f"{key}.json",value)
        findings.append(note(root,t,phot,visit,catalogue))
    report(output,shared,findings)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cache",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    main(args.cache,args.output)
