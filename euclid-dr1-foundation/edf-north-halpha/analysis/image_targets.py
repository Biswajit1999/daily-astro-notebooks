"""Extract and display WCS-registered VIS stamps from the released MER mosaics."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EUCLID = HERE.parents[1]
DAY2 = EUCLID / "2026-11-15-day02" / "analysis"
ARCHIVE = "https://nasa-irsa-euclid-dr1.s3.amazonaws.com/"
PANELS = [
    ("A and B", ("2700686070662453859", "2700684940662448691")),
    ("C", ("2697432168658721533",)),
    ("D", ("2693965274658805116",)),
    ("E", ("2703247763660016093",)),
    ("X", ("2693214850660403334",)),
    ("Y", ("2695057816657579082",)),
]


def extract(cache, source, products):
    key = products[f"{source.tileid}/VIS/science"]["key"]
    path = cache / Path(key).name
    if not path.is_file():
        raise FileNotFoundError(f"Cache the archive mosaic before extracting the stamp: {ARCHIVE}{key}")
    if path.stat().st_size != products[f"{source.tileid}/VIS/science"]["size"]:
        raise ValueError(f"File size differs from the MER manifest: {path}")
    with fits.open(path, memmap=True) as hdus:
        hdu = hdus[0]
        wcs = WCS(hdu.header)
        xy = wcs.world_to_pixel_values(source.ra, source.dec)
        cut = Cutout2D(hdu.data, xy, (60, 60), wcs=wcs, mode="strict", copy=True)
    if not np.isfinite(cut.data).any():
        raise ValueError(f"Empty stamp for {source.name}")
    header = cut.wcs.to_header()
    header["HIERARCH SOURCE"] = key
    header["MERID"] = str(source.name)
    return cut.data, header, key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="Directory holding original MER mosaics. Omit to use archived stamps.")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    parent = pd.read_csv(DAY2 / "observed_results/all_morphology_matched.csv.gz", dtype={"object_id": str}).set_index("object_id")
    cases = pd.read_csv(DAY2 / "targets/five_targets.csv", dtype={"object_id": str}).set_index("object_id")
    positions = parent[["ra", "dec"]].combine_first(cases[["ra_deg", "dec_deg"]].rename(columns={"ra_deg": "ra", "dec_deg": "dec"}))
    products = json.loads((DAY2 / "joint_audit/image_products.json").read_text())
    hdus = [fits.PrimaryHDU()]
    manifest = []
    fig, axes = plt.subplots(1, len(PANELS), figsize=(9, 1.65), layout="constrained")
    for (label, ids), ax in zip(PANELS, axes, strict=True):
        source = parent.loc[ids[0]]
        if args.cache is None:
            with fits.open(HERE / "target_vis_stamps.fits.gz") as archived:
                hdu = archived[label]
                image, header, key = hdu.data.copy(), hdu.header.copy(), hdu.header["SOURCE"]
        else:
            image, header, key = extract(args.cache, source, products)
            hdus.append(fits.ImageHDU(data=image, header=header, name=label))
        wcs = WCS(header)
        sky = positions.loc[list(ids)]
        cx, cy = wcs.world_to_pixel_values(sky.ra.to_numpy(), sky.dec.to_numpy())
        scale = float(proj_plane_pixel_scales(wcs)[0] * 3600)
        if not np.isclose(scale, 0.1, atol=.0001):
            raise ValueError(f"Unexpected image scale for {label}")
        low, high = np.nanpercentile(image, (22, 99.8))
        ax.imshow(np.arcsinh(5 * (image - low) / (high - low)), cmap="gray", origin="lower")
        for i, (x, y) in enumerate(zip(cx, cy, strict=True)):
            ax.plot(x, y, "o", mec="#ffc779", mfc="none", ms=9, mew=1.2)
            if len(ids) > 1:
                ax.text(x + 4, y + 4, ("A", "B")[i], color="#ffc779", fontsize=9)
        ax.plot((4, 4 + 1/scale), (5, 5), color="white", lw=1.6)
        ax.set(title=label, xticks=[], yticks=[])
        manifest.append({"panel": label, "mer_ids": list(ids), "tile": int(source.tileid),
                         "archive_url": ARCHIVE + key, "scale_arcsec_per_pixel": scale,
                         "image_pixel_sha256": hashlib.sha256(image.astype(">f4").tobytes()).hexdigest()})
    fig.savefig(args.output / "euclid_vis_targets.png", dpi=240)
    plt.close(fig)
    if args.cache is not None:
        with (args.output / "target_vis_stamps.fits.gz").open("wb") as stream:
            with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
                fits.HDUList(hdus).writeto(compressed)
    (args.output / "target_vis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
