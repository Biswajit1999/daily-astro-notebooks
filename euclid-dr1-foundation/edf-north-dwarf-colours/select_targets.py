"""Select three blue-core dE candidates and matched untagged Q1 controls."""
import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def vizier_table(raw, number):
    for section in raw.split("#Table")[1:]:
        if section.splitlines()[0].strip().endswith(f"_table{number}:"):
            lines = [line for line in section.splitlines()[1:] if line.strip() and not line.startswith("#")]
            return [{key: value.strip() for key, value in row.items()}
                    for row in csv.DictReader([lines[0], *lines[3:]], delimiter="\t")]
    raise ValueError(f"Missing table {number}")


def select(raw):
    classification, photometry, spectra = (vizier_table(raw, number) for number in (1, 2, 5))
    phot = {row["ID"]: row for row in photometry}
    spec_ids = {row["ID"] for row in spectra}
    sample = []
    for row in classification:
        values = phot.get(row["ID"])
        if (values is None or row["Morph"] != "dE" or row["Disturbed"] == "Yes"
                or not values["Area"] or not values["IEmag"]):
            continue
        mag, area = float(values["IEmag"]), float(values["Area"])
        if area < 12 or not 17.5 <= mag <= 21.0:
            continue
        sample.append({
            "object_id": row["ID"], "ra": float(row["RAJ2000"]), "dec": float(row["DEJ2000"]),
            "magn": mag, "area_arcsec2": area, "blue": row["Blue-cored"] == "Yes",
            "spectral_match_in_paper": row["ID"] in spec_ids, "disturbed": False,
        })
    controls = [obj for obj in sample if not obj["blue"]]
    tagged = sorted((obj for obj in sample if obj["blue"]),
                    key=lambda obj: (not obj["spectral_match_in_paper"], obj["magn"], obj["object_id"]))
    pairs = []
    for obj in tagged:
        local = []
        for ctrl in controls:
            ra_offset = (obj["ra"]-ctrl["ra"])*math.cos(math.radians(obj["dec"]))
            distance = math.hypot(ra_offset, obj["dec"]-ctrl["dec"])
            mag_offset = abs(obj["magn"]-ctrl["magn"])
            area_ratio = obj["area_arcsec2"]/ctrl["area_arcsec2"]
            if distance <= .30 and mag_offset <= .45 and .5 <= area_ratio <= 2:
                local.append((mag_offset+abs(math.log10(area_ratio)), ctrl["object_id"], ctrl))
        if local:
            _, _, best = min(local)
            pairs.append([obj, best])
            controls.remove(best)
        if len(pairs) == 3:
            return pairs
    raise ValueError("Fewer than three eligible pairs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogue", type=Path, help="Full VizieR J/A+A/711/A10 TSV export")
    parser.add_argument("--output", type=Path, default=HERE / "targets.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(select(args.catalogue.read_text()), indent=2) + "\n")


if __name__ == "__main__":
    main()
