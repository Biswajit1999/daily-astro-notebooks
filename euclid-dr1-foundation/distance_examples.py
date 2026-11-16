"""Convert the cited spectroscopic redshifts under a common reference cosmology."""
import csv
import sys

from astropy.cosmology import Planck18

SOURCES = (
    ("Day 3", "2695057816657579082", "DESI DR1", 0.905244, "", "https://arxiv.org/abs/2503.14745"),
    ("Day 5", "Carousel 1a", "VLT/MUSE", 0.96196, 0.00001, "https://doi.org/10.3847/1538-4357/ad65d3"),
    ("Day 5", "Carousel 2a", "VLT/MUSE", 0.96154, 0.00003, "https://doi.org/10.3847/1538-4357/ad65d3"),
)

DISTANCES = (
    ("comoving_gpc", Planck18.comoving_distance, "Gpc"),
    ("luminosity_gpc", Planck18.luminosity_distance, "Gpc"),
    ("lookback_gyr", Planck18.lookback_time, "Gyr"),
)


def main():
    writer = csv.writer(sys.stdout, lineterminator="\n")
    source_fields = ["series_day", "object", "instrument_or_release", "z_spec", "z_err", "reference"]
    quantity_fields = [f"{label}{suffix}" for label, _, _ in DISTANCES for suffix in ("", "_low", "_high")]
    writer.writerow([*source_fields, *quantity_fields])
    for source in SOURCES:
        z, dz = source[3:5]
        values = []
        for _, calculate, unit in DISTANCES:
            center = f"{calculate(z).to_value(unit):.6f}"
            limits = [f"{calculate(z+sign*dz).to_value(unit):.6f}" for sign in (-1, 1)] if dz else ["", ""]
            values.extend([center, *limits])
        writer.writerow([*source, *values])


if __name__ == "__main__":
    main()
