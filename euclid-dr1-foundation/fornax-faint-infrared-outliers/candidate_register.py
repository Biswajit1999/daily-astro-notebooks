"""Join the fixed shortlist, public source identifiers, and visual classifications."""
import csv
import json
from pathlib import Path

ROOT = Path("results")
NOTES = {
    "F01": ("Compact in VIS; no bright diffraction through target; a brighter source lies north.",
            "Ordinary star or galaxy remains plausible; tested mid-T standards fit poorly."),
    "F02": ("Strong nearby bright-star halo and diffraction; elongated VIS source; flag contamination.",
            "Blended or extended galaxy, stellar-halo background residual, or compact source in a crowded field."),
    "F03": ("Compact central counterpart; bright object near western image edge, with no obvious streak through target.",
            "Galaxy or ordinary star remains plausible; tested mid-T standards fit poorly."),
}

with (ROOT / "screen_candidates.csv").open() as f:
    data = list(csv.DictReader(f))
arch = json.loads((ROOT / "external_audit.json").read_text())["targets"]
spectra = json.loads((ROOT / "nisp_spectra.json").read_text())
selected = []
for row in data:
    label = row["audit_id"]
    row["observed_bands"] = "Euclid VIS,Y,J,H"
    row["classification"] = "Unconstrained"
    row["redshift_distance"] = "Unconstrained"
    if label:
        folder = ROOT / "audit" / label
        video = arch[label]["VIDEO_CAT_DR5"]["matches"][0]
        row.update({"phz_object_id": row["object_id"], "spe_class_or_galaxy_id": "",
                    "sir_object_id": row["object_id"] if spectra[label] else "",
                    "sir_grisms": ";".join(r["lrange"] for r in spectra[label]),
                    "video_dr5_id": video["VIDEOID"], "video_sep_arcsec": video["angular_separation_arcsec"],
                    "artifact_checks": NOTES[label][0] + " Detector-level persistence, variability and motion remain unchecked.",
                    "alternate_interpretations": NOTES[label][1],
                    "cutouts": str(folder / "cutouts.webp"),
                    "spectrum": str(folder / "spectrum.png") if spectra[label] else "",
                    "observed_bands": "Euclid VIS,Y,J,H; Blanco DECam z; VISTA VIRCAM Z,Y,J,H,Ks (F02 Z flagged)",
                    "audit": "Completed image and archive check"})
    else:
        row.update({"artifact_checks":"MER flags only; image and external crossmatch pending",
                    "alternate_interpretations":"Galaxy, QSO, star, ultracool dwarf, blend or artifact",
                    "audit":"Uninspected by fixed three-object rule"})
    selected.append(row)
fields = list(dict.fromkeys(key for row in selected for key in row))
with (ROOT / "candidate_register.csv").open("w") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(selected)
