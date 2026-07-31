"""Extract compact, reproducible Kepler PDCSAP tables for Audit Batch 2."""
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD = Path("/tmp/astro-batch2/mastDownload/Kepler")


def extract(kic: str, destination: Path) -> None:
    rows = []
    products = sorted(DOWNLOAD.glob(f"kplr{kic}_lc_*/kplr{kic}-*_llc.fits"))
    if not products:
        raise FileNotFoundError(f"No downloaded products for KIC {kic}")
    for product in products:
        with fits.open(product, memmap=False) as hdul:
            header = hdul[0].header
            data = hdul[1].data
            frame = pd.DataFrame({
                "time_bkjd": np.asarray(data["TIME"], dtype=float),
                "pdcsap_flux": np.asarray(data["PDCSAP_FLUX"], dtype=float),
                "pdcsap_flux_err": np.asarray(data["PDCSAP_FLUX_ERR"], dtype=float),
                "quality": np.asarray(data["SAP_QUALITY"], dtype=np.int64),
            })
            frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
            good = frame["quality"].eq(0)
            median = frame.loc[good, "pdcsap_flux"].median()
            frame["flux_normalized"] = frame["pdcsap_flux"] / median
            frame["error_normalized"] = frame["pdcsap_flux_err"] / median
            frame["quarter"] = int(header.get("QUARTER", -1))
            frame["product"] = product.name
            rows.append(frame)
    output = pd.concat(rows, ignore_index=True).sort_values("time_bkjd")
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False)
    print(f"{kic}: {len(products)} products, {len(output):,} cadences -> {destination}")


def main() -> None:
    extract("008120608", ROOT / "mast/2026-07-30-kepler-lightcurve-kepler186f/kepler186_all_quarters.csv")
    extract("010666592", ROOT / "mast/2026-07-30-periodogram-hat-p-7b/hatp7_all_quarters.csv")


if __name__ == "__main__":
    main()
