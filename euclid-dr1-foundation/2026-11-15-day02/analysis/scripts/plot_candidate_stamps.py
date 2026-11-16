"""Make a quick-look VIS and NISP sheet for the highest-ranked pilot objects."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from audit_grism_halpha import DAY02, get_hats_spectrum, fit_window, fetch_archive_file
from audit_secondary_lines import LINES
from screen_interesting_objects import read_subset

def local_centroid(window, centre):
    """Refit a line centre over fixed pixels, with a ±40 Å local search."""
    used = window.loc[window.usable]
    x = used.wavelength.to_numpy() - centre
    flux = used.signal.to_numpy()
    noise = np.sqrt(used["var"].to_numpy())
    grid = np.arange(-40.0, 41.0, 1.0)
    scores = []
    for delta in grid:
        profile = np.exp(-0.5 * ((x - delta) / 30.0)**2)
        design = np.column_stack((np.ones_like(x), x / 250.0, profile))
        weighted = design / noise[:, None]
        coefficients = np.linalg.lstsq(weighted, flux / noise, rcond=None)[0]
        residual = (flux - design @ coefficients) / noise
        scores.append(np.sum(residual**2) if coefficients[2] > 0 else np.inf)
    if not np.isfinite(scores).any():
        return None
    best = int(np.argmin(scores))
    return {
        "offset_A": float(grid[best]), "at_grid_edge": best in (0, len(grid) - 1),
        "wavelength_A": float(centre + grid[best]), "usable_bins": len(used),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-cache", type=Path, required=True)
    parser.add_argument("--sir-cache", type=Path, required=True)
    args = parser.parse_args()
    out = DAY02 / "targets"
    args.image_cache.mkdir(parents=True, exist_ok=True)
    args.sir_cache.mkdir(parents=True, exist_ok=True)
    repeat = pd.read_csv(out / "repeatable_halpha.csv").head(3)
    multi = pd.read_csv(out / "multi_line_candidates.csv")
    multi = multi.loc[multi.clean | multi.external_agreement].head(3)
    shortlist = pd.concat([repeat, multi]).drop_duplicates("object_id")
    spectra, _ = read_subset(args.sir_cache, shortlist)
    products = json.loads((DAY02 / "joint_audit" / "image_products.json").read_text())
    fig, axes = plt.subplots(len(shortlist), 3, figsize=(10.4, 2.05 * len(shortlist)),
                             squeeze=False, layout="constrained")
    diagnostics = []
    with ExitStack() as stack:
        images = {}
        for row, panels in zip(shortlist.itertuples(index=False), axes, strict=True):
            if row.tileid not in images:
                key = products[f"{row.tileid}/VIS/science"]["key"]
                path = fetch_archive_file(key, args.image_cache / Path(key).name)
                hdu = stack.enter_context(fits.open(path, memmap=True))[0]
                images[row.tileid] = (hdu, WCS(hdu.header))
            hdu, wcs = images[row.tileid]
            x, y = wcs.world_to_pixel_values(row.ra, row.dec)
            ix, iy = int(round(float(x))), int(round(float(y)))
            half = 45
            if min(ix, iy, hdu.shape[1] - ix, hdu.shape[0] - iy) < half:
                raise ValueError(f"VIS cutout extends beyond its parent tile for {row.object_id}")
            tile = hdu.section[iy-half:iy+half+1, ix-half:ix+half+1]
            lo, hi = np.nanpercentile(tile, (5, 99.65))
            data = np.arcsinh(8 * (tile - lo) / (hi - lo)) if hi > lo else tile
            panels[0].imshow(data, origin="lower", cmap="gray_r")
            panels[0].plot(x - ix + half, y - iy + half, "+", color="#bb402d", markersize=6)
            panels[0].set_title(str(row.object_id), fontsize=9)
            panels[0].set_xticks([])
            panels[0].set_yticks([])
            chosen = getattr(row, "blue_secondary_line", "")
            blue_line = chosen if isinstance(chosen, str) else "OIII5008"
            ha_grism = getattr(row, "ha_grism", None)
            grisms = (ha_grism if isinstance(ha_grism, str) else "RGS", "BGS")
            for panel, grism, line in zip(panels[1:], grisms, ("Halpha", blue_line), strict=True):
                data, count = get_hats_spectrum(spectra, row.object_id, row.tileid, grism)
                if count != 1:
                    raise ValueError(f"Missing {grism} spectrum for {row.object_id}")
                centre = LINES[line] * (1 + row.spe_z)
                result, plot = fit_window(data, centre)
                dx = plot.wavelength - centre
                panel.plot(dx, plot.signal.where(plot.ndith > 0), color="0.65", lw=1)
                good = plot.usable
                panel.scatter(dx[good], plot.signal[good], s=7, color="#216697")
                if "model" in plot:
                    panel.plot(dx, plot.model, lw=1, color="#bb402d")
                    centroid = local_centroid(plot, centre)
                    if centroid is not None:
                        diagnostics.append({"object_id": row.object_id, "grism": grism, "line": line,
                                            "spe_prediction_A": centre, **centroid,
                                            "apparent_z": centroid["wavelength_A"] / LINES[line] - 1})
                panel.axvline(0, color="0.35", ls=":", lw=0.75)
                label = "strict fit" if result["status"] == "fitted" else "coverage or mask limited"
                panel.set_title(f"{grism} · {line} · {label}", fontsize=8)
                panel.set_xlim(-250, 250)
                panel.tick_params(labelsize=8)
    fig.supxlabel("Spectral panels show wavelength offset from SPE prediction (Å)")
    fig.savefig(out / "candidate_stamps.png", dpi=125)
    plt.close(fig)
    pd.DataFrame(diagnostics).to_csv(out / "local_centroids.csv", index=False)


if __name__ == "__main__":
    main()
