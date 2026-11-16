"""Fit concentric disc isophotes and test two published IC 1914 positions."""
import argparse
import csv
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astropy.io import fits
import astropy.units as u
from astropy.wcs import WCS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter, median_filter
from scipy.optimize import least_squares
from scipy.stats import median_abs_deviation

HERE = Path(__file__).resolve().parent
BANDS = {"restored_vis": "Euclid VIS, restored", "legacy_r": "Legacy DR10 r",
         "h": "Euclid NISP H"}
MODELS = ("s4g", "constant", "varying")
ASYM_KNOTS = np.array([0, 35, 65, 90, 115, 145, 180, 210, 265])
IDS = ("IC1914-01", "IC1914-03")
KNOTS = np.array([0, 12, 22, 32, 43, 55, 67, 79, 91, 103, 116, 130,
                  145, 162, 180, 202, 228, 265, 340])
RADIUS = 5.0


def load_image(cache, row, band):
    name = row["object"]
    source = "vis" if band == "restored_vis" else band
    image, header = fits.getdata(cache / f"{name}_{source}.fits", header=True)
    wcs = WCS(header).celestial
    step = np.sqrt(abs(np.linalg.det(wcs.pixel_scale_matrix))) * 3600
    factor = 5 if step < 0.2 else 1
    valid = np.isfinite(image) & (image != 0)
    if band == "restored_vis":
        background, sky_header = fits.getdata(cache / f"{name}_vis_sky.fits", header=True)
        sky_wcs = WCS(sky_header).celestial
        if image.shape != background.shape or not wcs.wcs.compare(sky_wcs.wcs, tolerance=1e-10):
            raise ValueError("Restored VIS requires co-registered image and background cutouts")
        image = image + background
    ny, nx = (np.array(image.shape) // factor) * factor
    blocks = np.ma.array(image, mask=~valid)[:ny, :nx].reshape(ny//factor, factor, nx//factor, factor)
    image = np.ma.median(blocks, axis=(1, 3)).filled(np.nan)
    image[blocks.count(axis=(1, 3)) <= factor**2//2] = np.nan
    centre = SkyCoord(float(row["ra"]), float(row["dec"]), unit="deg")
    yy, xx = np.indices(image.shape)
    middle = (factor - 1) / 2
    sky = wcs.pixel_to_world(factor*xx+middle, factor*yy+middle)
    east, north = (x.to_value(u.arcsec) for x in centre.spherical_offsets_to(sky))
    return image, east, north, factor*step, header.get("BUNIT", "nanomaggy / pixel")


def offsets(east, north, pa):
    return east*np.sin(pa) + north*np.cos(pa), east*np.cos(pa) - north*np.sin(pa)


def geometry(parameters, radius):
    q, pa, dq, dpa = parameters
    transition = np.tanh((radius-90)/48)
    return q+dq*transition, pa+dpa*transition


def ellipse_radius(east, north, parameters):
    """Invert a nested family of ellipses by Newton iteration."""
    q, pa, dq, dpa = parameters
    major, minor = offsets(east, north, pa)
    radius = np.hypot(major, minor/q)
    if dq == dpa == 0:
        return radius
    for _ in range(7):
        q_r, pa_r = geometry(parameters, radius)
        slope = (1-np.tanh((radius-90)/48)**2)/48
        major, minor = offsets(east, north, pa_r)
        scaled = minor/q_r
        metric = np.hypot(major, scaled)
        deriv = (major*minor*dpa*slope - scaled*(major*dpa+scaled*dq)*slope/q_r)
        deriv /= np.maximum(metric, 1e-9)
        radius = np.maximum(0, radius + (metric-radius)/np.maximum(1-deriv, .35))
    return radius


def clean_pixels(image, step, fixed_radius):
    finite = np.isfinite(image)
    fill = np.where(finite, image, np.nanmedian(image))
    width = 2*round(2.0/step)+1
    local = median_filter(fill, size=width)
    highpass = fill-local
    outskirts = finite & (fixed_radius > 150)
    noise = median_abs_deviation(highpass[outskirts], scale="normal")
    local_noise = median_filter(np.abs(highpass), size=width)/.67449
    bright = np.abs(highpass) > 5*np.maximum(noise, local_noise)
    distance = int(np.ceil(1.0/step))
    y,x = np.ogrid[-distance:distance+1, -distance:distance+1]
    expanded = binary_dilation(bright, structure=(x*x+y*y) <= (1.0/step)**2)
    return finite & ~expanded, noise


def solve(img, x, y, fixed, mask, noise, model):
    # Stride fixed on the image grid. Robust loss limits the effect of remaining knots.
    iy, ix = np.nonzero(mask)
    use = (iy % 4 == 0) & (ix % 4 == 0)
    iy, ix = iy[use], ix[use]
    e, n, values = x[iy,ix], y[iy,ix], img[iy,ix]
    r0 = ellipse_radius(e, n, fixed)
    windows = np.abs(r0[:,None]-KNOTS[None,:]) <= 8
    measured = [(k, np.median(values[window])) for k,window in zip(KNOTS, windows.T) if window.sum() >= 8]
    ri, fi = np.array(measured).T
    baseline = np.interp(r0, ri, fi)
    unit = max(median_abs_deviation((values-baseline)[r0>130], scale="normal"), noise)
    profile = np.interp(KNOTS, ri, fi)/unit
    fit_scale = 1+.08*np.abs((baseline-np.median(fi[-3:]))/unit)
    size = {"s4g":0, "constant":2, "varying":4}[model]
    low = [.38, fixed[1]-.70, -.125, -.24]
    high = [.73, fixed[1]+.70, .125, .24]

    def residual(params):
        geo = np.concatenate((params[:size], fixed[size:]))
        radii = ellipse_radius(e, n, geo)
        predicted = np.interp(radii, KNOTS, params[size:])
        regular = np.diff(params[size:], n=2)
        return np.r_[(predicted-values/unit)/fit_scale, .25*regular]

    result = least_squares(residual, np.r_[fixed[:size], profile],
                           bounds=(np.r_[low[:size], np.full(len(KNOTS), -np.inf)],
                                   np.r_[high[:size], np.full(len(KNOTS), np.inf)]),
                           loss="soft_l1", max_nfev=100, ftol=1e-5, xtol=1e-5)
    if not result.success:
        raise RuntimeError(f"{model}: {result.message}")
    return np.r_[result.x[:size], fixed[size:]], result.x[size:]*unit


def asymmetry_basis(east, north, params):
    radius = ellipse_radius(east, north, params)
    q, pa = geometry(params, radius)
    major, minor = offsets(east, north, pa)
    theta = np.arctan2(minor/q, major)
    azimuth = np.column_stack((np.cos(theta), np.sin(theta), np.cos(2*theta), np.sin(2*theta)))
    weights = np.column_stack([np.interp(radius, ASYM_KNOTS, v) for v in np.eye(len(ASYM_KNOTS))])
    return (weights[:,:,None]*azimuth[:,None,:]).reshape(len(radius), -1)


def fit_asymmetry(image, east, north, mask, params, profile):
    rows, cols = np.indices(image.shape)
    use = mask & (rows % 4 == 0) & (cols % 4 == 0)
    x,y = east[use],north[use]
    values = image[use] - np.interp(ellipse_radius(x,y,params), KNOTS, profile)
    unit = median_abs_deviation(values, scale="normal")
    design = asymmetry_basis(x,y,params)
    # Shrink the knot amplitudes and penalise abrupt changes in radius.
    n = design.shape[1]
    curvature = np.diff(np.eye(n).reshape(len(ASYM_KNOTS),4,n),n=2,axis=0).reshape(-1,n)
    penalty = np.vstack((.5*np.eye(n), 3*curvature))
    fit = least_squares(
        lambda coef: np.r_[design@coef-values/unit, penalty@coef],
        np.zeros(n), loss="soft_l1", max_nfev=35
    )
    if not fit.success:
        raise RuntimeError(f"Fourier asymmetry: {fit.message}")
    return fit.x*unit


def angle_holds(east, north):
    theta = np.mod(np.arctan2(north, east), 2*np.pi)
    return (np.floor(theta/(np.pi/8)).astype(int)) % 4


def evaluate(image, east, north, train, base, noise, fixed):
    hold = angle_holds(east, north)
    records = []
    for fold in range(4):
        test = base & (hold==fold)
        measured = {"fold": fold, "n_outer_test": int(test.sum())}
        for model in MODELS:
            params, profile = solve(image, east, north, fixed, train & (hold!=fold), noise, model)
            radii = ellipse_radius(east[test], north[test], params)
            residual = image[test]-np.interp(radii, KNOTS, profile)
            measured[model] = float(np.median(np.abs(residual)))
            if model == "varying":
                coef = fit_asymmetry(image,east,north,train & (hold!=fold),params,profile)
                correction = asymmetry_basis(east[test],north[test],params)@coef
                measured["varying_m12"] = float(np.median(np.abs(residual-correction)))
        records.append(measured)
    return records


def candidate_apertures(candidates, east, north, fixed, usable):
    """Freeze identical nonoverlapping controls before comparing the models."""
    pa, q = fixed[1], fixed[0]
    sample = {}
    all_targets = [(c["east"],c["north"]) for c in candidates]
    for candidate in candidates:
        pos = candidate["east"], candidate["north"]
        major, minor = offsets(*pos, pa)
        phase = np.arctan2(minor/q, major)
        rho = np.hypot(major, minor/q)
        positions = [pos]
        for angle in phase + np.deg2rad(np.arange(5,360,5)):
            a,b = rho*np.cos(angle), q*rho*np.sin(angle)
            e,n = a*np.sin(pa)+b*np.cos(pa), a*np.cos(pa)-b*np.sin(pa)
            if not 40 <= np.hypot(e,n) <= 105:
                continue
            if any(np.hypot(e-u,n-v) < 2*RADIUS for u,v in all_targets+positions):
                continue
            positions.append((e,n))
        masks = []
        for e,n in positions:
            circle = (east-e)**2 + (north-n)**2 <= RADIUS**2
            mask = circle & usable
            if mask.sum() >= .65*circle.sum() and circle.sum() > 20:
                masks.append(mask)
            elif not masks:
                raise ValueError(f"Candidate {candidate['id']} aperture lacks coverage")
        sample[candidate["id"]] = masks
    return sample


def aperture_stats(resid, masks):
    spot, *control = [float(np.mean(resid[mask])) for mask in masks]
    median = np.median(control)
    return {"mean": spot, "control_median": float(median), "excess": float(spot-median),
            "n_fainter": sum(c < spot for c in control), "n_control": len(control),
            "rank": sum(c < spot for c in control)/len(control),
            "control_values": control, "n_candidate_pixels": int(masks[0].sum())}


def run_band(cache, row, band, fixed, candidates):
    image,east,north,step,unit = load_image(cache,row,band)
    fixed_radius = ellipse_radius(east,north,fixed)
    usable,noise = clean_pixels(image,step,fixed_radius)
    available = usable & (fixed_radius >= 12) & (fixed_radius <= 210)
    sep = np.minimum.reduce([np.hypot(east-c["east"],north-c["north"]) for c in candidates])
    apertures = candidate_apertures(candidates,east,north,fixed,usable)
    models, measurements = {}, {}
    for exclusion in (12,18):
        entries = {}
        for model in MODELS:
            params, profile = solve(image,east,north,fixed,available&(sep>=exclusion),noise,model)
            elliptical = ellipse_radius(east,north,params)
            qr, pr = geometry(params, np.array([45,90,135]))
            if np.max(np.abs(ellipse_radius(*project_test(params),params)-KNOTS[1:-1,None])) > 0.03:
                raise ValueError(f"{model} ellipse family did not invert reliably")
            residual = image-np.interp(elliptical,KNOTS,profile)
            entries[model] = {"axis_ratio_45_90_135": qr.tolist(),
                              "pa_deg_45_90_135": np.rad2deg(pr).tolist(),
                              "profile":profile.tolist(),"geometry":params.tolist(),
                              "candidates":{key:aperture_stats(residual,masks) for key,masks in apertures.items()}}
            if exclusion==12:
                models[model] = residual
            if model=="varying":
                coef = fit_asymmetry(image,east,north,available&(sep>=exclusion),params,profile)
                correction = np.empty_like(residual)
                for rows in np.array_split(np.arange(len(image)), 8):
                    x,y = east[rows].ravel(),north[rows].ravel()
                    correction[rows] = (asymmetry_basis(x,y,params)@coef).reshape(len(rows),-1)
                asymmetric = residual-correction
                entries["varying_m12"] = {
                    "fourier_coefficients":coef.reshape(-1,4).tolist(),
                    "candidates":{key:aperture_stats(asymmetric,masks) for key,masks in apertures.items()}
                }
                if exclusion==12:
                    models["varying_m12"] = asymmetric
        measurements[str(exclusion)] = entries
    base = available & (sep>=12)
    cv = evaluate(image,east,north,base,base&(fixed_radius>=80)&(fixed_radius<=145),noise,fixed)
    return {"unit":unit,"pixel_arcsec":step,"highpass_noise":float(noise),
            "measurements":measurements,"angular_holdouts":cv}, (image,east,north,step,usable,models)


def project_test(params):
    radius = KNOTS[1:-1,None]
    phase = np.linspace(0,2*np.pi,30,endpoint=False)
    q,p = geometry(params,radius)
    major,minor = radius*np.cos(phase),radius*q*np.sin(phase)
    return major*np.sin(p)+minor*np.cos(p),major*np.cos(p)-minor*np.sin(p)


def draw(data, candidates, output):
    fig, axes = plt.subplots(3,5,figsize=(14,9),layout="constrained")
    for (band, (image,east,north,step,good,residuals)), panels in zip(data.items(), axes):
        mask = good & (np.hypot(east,north)>70) & (np.hypot(east,north)<110)
        scale = 2.5*median_abs_deviation(residuals["s4g"][mask],scale="normal")
        extent = [-east[0,0]-step/2,-east[0,-1]+step/2,north[0,0]-step/2,north[-1,0]+step/2]
        med,high = np.nanpercentile(image,[30,98])
        panels[0].imshow(np.arcsinh((image-med)*12/(high-med)),origin="lower",extent=extent,
                         cmap="gray",vmin=-.2,vmax=3.5)
        for ax, residual in zip(panels[1:],residuals.values()):
            weights = gaussian_filter(good.astype(float),1.5/step)
            blur = gaussian_filter(np.where(good,residual,0),1.5/step)/np.maximum(weights,1e-9)
            ax.imshow(np.where(weights>.65,blur,np.nan),origin="lower",extent=extent,
                      cmap="RdBu_r",vmin=-scale,vmax=scale)
        for i,ax in enumerate(panels):
            for candidate in candidates:
                x,y=-candidate["east"],candidate["north"]
                ax.add_patch(Circle((x,y),5,edgecolor="#36cf96",facecolor="none",linewidth=1.1))
                ax.text(x+6,y+4,candidate["id"][-2:],color="#147450" if i else "#58ffbb",fontsize=8,
                        bbox=dict(facecolor="white" if i else "black",alpha=.75,edgecolor="none",pad=.6))
            ax.set(xlim=(-105,105),ylim=(-105,105),xticks=[],yticks=[])
        panels[0].set_ylabel(BANDS[band])
    for ax,title in zip(axes[0],["Observed cutout","Fixed S4G geometry","Fitted constant ellipse","Radius-dependent ellipse","Plus broad asymmetry"]):
        ax.set_title(title)
    fig.savefig(output/"disc_residuals.png",dpi=115)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    parent=HERE.parent/"data"
    with (parent/"targets.csv").open() as f:
        row=next(r for r in csv.DictReader(f) if r["object"]=="IC1914")
    sources=json.loads((parent/"aperture_checks.json").read_text())["candidates"]
    candidates=[{k:c[k] for k in ("id","ra","dec","east","north")} for c in sources if c["id"] in IDS]
    if {c["id"] for c in candidates} != set(IDS):
        raise ValueError("Missing an original IC 1914 coordinate")
    fixed=np.array([1-float(row["ellip1_25p5"]),np.deg2rad(float(row["pa1_25p5"])),0,0])
    results, data = {}, {}
    for band in BANDS:
        results[band],data[band] = run_band(args.cache,row,band,fixed,candidates)
        print(f"{band} fit and angular holdouts complete",flush=True)
    draw(data,candidates,args.output)
    report = {"target":"IC1914","candidate_positions":candidates,"profile_knots_arcsec":KNOTS.tolist(),
              "asymmetry_knots_arcsec":ASYM_KNOTS.tolist(),"bands":results}
    (args.output/"measurements.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
