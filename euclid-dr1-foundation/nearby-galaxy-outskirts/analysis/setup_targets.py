import argparse
from pathlib import Path
from urllib.request import urlretrieve

import astropy.units as u
from astropy.io import ascii
from mocpy import MOC
import numpy as np

S4G = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=s4gcat&spatial=none&outfmt=1"
MOC_URL = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com/dr1/MOC/euclid_dr1_mer_catalogue_wide_survey.moc.fits"


def main():
    parser = argparse.ArgumentParser(description="Select the fixed S4G galaxy sample.")
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    catalog_file = args.cache/"s4g.tbl"
    moc_file = args.cache/"mer_wide.moc.fits"
    if not catalog_file.exists():
        urlretrieve(S4G, catalog_file)
    if not moc_file.exists():
        urlretrieve(MOC_URL, moc_file)
    table = ascii.read(catalog_file, format="ipac")
    moc = MOC.from_fits(moc_file)
    in_moc = moc.contains_lonlat(np.asarray(table["ra"])*u.deg, np.asarray(table["dec"])*u.deg)
    eligible = np.ma.filled(
        (table["sma1_25p5"] >= 60) & (table["sma1_25p5"] <= 120)
        & (table["ellip1_25p5"] >= .4) & (table["dmean"] > 0) & (table["dmean"] <= 25), False
    )
    sample = table[in_moc & eligible]
    sample.sort(["sma1_25p5", "object"], reverse=True)
    cols = ["object", "ra", "dec", "sma1_25p5", "ellip1_25p5", "pa1_25p5", "dmean", "t"]
    sample[:8][cols].write(args.cache/"targets.csv", format="ascii.csv", overwrite=True)
    print(f"{len(table)} S4G galaxies, {sum(in_moc)} in MOC, {len(sample)} eligible, {min(len(sample),8)} selected")


if __name__ == "__main__":
    main()
