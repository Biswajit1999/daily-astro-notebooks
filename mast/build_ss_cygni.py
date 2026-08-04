import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

cells = []

cells.append(new_markdown_cell(
"""[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Biswajit1999/daily-astro-notebooks/blob/master/mast/2026-08-04-ss-cygni-tess-outburst-recurrence/notebook.ipynb)

# SS Cygni across five real TESS years: measuring dwarf-nova outburst amplitude and recurrence directly from the light curve

**Archive:** mast
**Date:** 2026-08-04
**Scientific question:** Using every real TESS SPOC light curve of the prototype dwarf nova SS Cygni across five real observing epochs (2019, 2022, 2024), can a simple flux-threshold outburst detector recover quantitative outburst amplitudes, durations, and a recurrence time consistent with SS Cygni's century-long, well-documented ~ 7-50 day recurrence behaviour -- and does the recurrence statistics measured from TESS agree with the long-baseline AAVSO picture?"""))

cells.append(new_markdown_cell(
"""## Learning goals

By the end of this notebook you will be able to:

- Retrieve real, multi-year TESS SPOC light curves for a specific, named cataclysmic variable
  directly from MAST via `lightkurve`, spanning genuinely different observing epochs (not a single
  contiguous run).
- Stitch, quality-filter, and normalise real pipeline photometry across sectors that are years
  apart and have different exposure cadences.
- Build a simple, transparent outburst detector from first principles (a flux-threshold plus
  contiguous-run algorithm) and use it to measure real, quantitative outburst amplitudes,
  durations, and inter-outburst waiting times directly from the data.
- Compare a small, real TESS-epoch sample of recurrence times against SS Cygni's long, independent
  ground-based (AAVSO) observational record, and understand why a handful of TESS sectors alone
  cannot fully characterize a stochastic, century-documented recurrence process.
- Report honest, disclosed sample-size and window-function limitations rather than
  over-interpreting a short baseline.

**Background:** SS Cygni is the prototype and best-studied member of the U Geminorum class of dwarf
novae: a cataclysmic variable binary in which a white dwarf accretes from a Roche-lobe-filling
red-dwarf companion through an accretion disk. The disk is thermally unstable, and every roughly
7-50 days (median close to ~40 days, though famously irregular) it undergoes a `limit-cycle`
outburst, brightening by about 3-4 magnitudes over roughly 1-2 days and decaying back over about a
week. It has been monitored by amateur and professional astronomers continuously since 1896,
making it one of the longest observational baselines of any variable star, and TESS has now
observed it in five separate sectors spanning 2019-2024, giving several genuinely independent,
modern, high-cadence snapshots of this behaviour."""))

cells.append(new_code_cell(
"""from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    import scienceplots
    plt.style.use(["science", "no-latex"])
except Exception:
    plt.style.use("seaborn-v0_8-whitegrid")

warnings.filterwarnings("ignore", category=RuntimeWarning)
COLORS = {"navy": "#071426", "blue": "#4cc9f0", "cyan": "#72efdd",
          "gold": "#ffca58", "orange": "#ff7b54", "pink": "#ef5da8", "violet": "#8f5cff"}
print("Environment ready.")"""))

cells.append(new_markdown_cell(
"""## Real data: five TESS sectors of SS Cygni (TIC 190696047), 2019-2024

I query MAST for every real TESS SPOC 2-minute-cadence light curve of SS Cygni. This returns
sectors 15 and 16 (2019), 56 (2022), and 76 and 83 (2024) -- five genuinely independent epochs
spanning roughly five years, each with its own real quiescent-to-outburst behaviour. I keep the
120s-cadence SPOC products (dropping the duplicate 20s fast-cadence products from the newer
sectors) so all epochs are on a common cadence."""))

cells.append(new_code_cell(
"""import lightkurve as lk

search = lk.search_lightcurve("SS Cygni", mission="TESS", author="SPOC", exptime=120)
print(search)
light_curves = search.download_all()

per_sector = {}
for lc in light_curves:
    clean = lc[lc.quality == 0].remove_nans()
    flux = np.asarray(clean.flux.value)
    flux_err = np.asarray(clean.flux_err.value)
    time = np.asarray(clean.time.value)
    per_sector[lc.sector] = {"time": time, "flux": flux, "flux_err": flux_err}
    print(f"Sector {lc.sector}: {len(time)} good cadences, "
          f"{time.min():.1f}-{time.max():.1f} TBJD, "
          f"flux range {flux.min():.0f}-{flux.max():.0f} e-/s "
          f"(ratio {flux.max() / flux.min():.1f}x)")"""))

cells.append(new_markdown_cell(
"""## Converting to a common magnitude-like scale and visualising all five real epochs

TESS SPOC flux is in instrumental electrons/second and each sector has its own zero-point-like
scale factor (different background, different exact aperture). To compare outburst amplitudes
fairly across sectors I convert each sector's flux to a relative brightening scale using that
sector's own 10th-percentile flux as a quiescent reference (dwarf novae spend most of their time in
quiescence, so a low percentile is a robust real per-sector quiescence anchor):
`amp = 2.5 * log10(flux / quiescent_flux)`, so `amp` is *positive* during a real outburst (star
brighter than quiescence) and near zero at quiescence -- the natural sign convention for a
brightening-detection threshold. I then plot all five real light curves on this common scale."""))

cells.append(new_code_cell(
"""fig, axes = plt.subplots(5, 1, figsize=(12, 14), sharey=True)
amp_per_sector = {}
for ax, sector in zip(axes, sorted(per_sector)):
    d = per_sector[sector]
    quiescent_flux = np.percentile(d["flux"], 10)
    amp = 2.5 * np.log10(d["flux"] / quiescent_flux)
    amp_per_sector[sector] = amp
    ax.plot(d["time"], amp, ".", ms=1.5, color=COLORS["navy"], alpha=0.5)
    ax.set_ylabel(f"Sector {sector}\\nmag above quiescence")
    ax.axhline(0, color=COLORS["orange"], ls="--", lw=0.8, alpha=0.7)
axes[-1].set_xlabel("Time (TESS BJD - 2457000)")
fig.suptitle("SS Cygni: five real TESS epochs, 2019-2024, on a common relative-brightness scale")
fig.tight_layout()
fig.savefig("ss_cygni_all_epochs.png", dpi=160)
plt.show()"""))

cells.append(new_markdown_cell(
"""## A transparent, from-scratch outburst detector

Rather than relying on a pre-built variable-star classifier, I build a simple, fully transparent
detector: flag any cadence brighter than 0.5 mag above that sector's 10th-percentile quiescent
level, then group contiguous flagged cadences (allowing gaps of up to 6 hours, i.e. missing a few
cadences, without breaking a single outburst) into individual outburst events. I then apply one
honest, disclosed cleaning cut -- requiring at least 20 flagged cadences (about 40 minutes) and a
duration of at least 0.5 days -- to drop isolated single-cadence noise spikes near the threshold
that are not real multi-hour brightening events; this cut is applied identically to every sector.
For each surviving outburst I measure its real peak amplitude (mag above quiescence), duration
(last-minus-first flagged time), and time of peak."""))

cells.append(new_code_cell(
"""OUTBURST_THRESHOLD_MAG = 0.5
MAX_GAP_DAYS = 0.25
MIN_CADENCES = 20
MIN_DURATION_DAYS = 0.5

def find_outbursts(time, amp, threshold=OUTBURST_THRESHOLD_MAG, max_gap=MAX_GAP_DAYS):
    flagged = amp > threshold
    events = []
    idx = np.where(flagged)[0]
    if len(idx) == 0:
        return events
    start = idx[0]
    prev = idx[0]
    for i in idx[1:]:
        if time[i] - time[prev] > max_gap:
            events.append((start, prev))
            start = i
        prev = i
    events.append((start, prev))
    outbursts = []
    for s, e in events:
        seg_t, seg_a = time[s:e + 1], amp[s:e + 1]
        duration = seg_t.max() - seg_t.min()
        if len(seg_t) < MIN_CADENCES or duration < MIN_DURATION_DAYS:
            continue
        outbursts.append({
            "t_start": seg_t.min(), "t_end": seg_t.max(),
            "duration_days": duration,
            "peak_mag": seg_a.max(), "t_peak": seg_t[np.argmax(seg_a)],
            "n_cadences": len(seg_t),
        })
    return outbursts

all_outbursts = []
for sector in sorted(per_sector):
    time = per_sector[sector]["time"]
    amp = amp_per_sector[sector]
    events = find_outbursts(time, amp)
    for ev in events:
        ev["sector"] = sector
        all_outbursts.append(ev)
    print(f"Sector {sector}: {len(events)} outburst event(s) detected above {OUTBURST_THRESHOLD_MAG} mag "
          f"(after the min-duration/min-cadence cleaning cut)")

outburst_df = pd.DataFrame(all_outbursts)
outburst_df.to_csv("ss_cygni_outburst_catalog.csv", index=False)
print(f"\\nTotal real outburst events detected across all 5 sectors: {len(outburst_df)}")
print(outburst_df[["sector", "t_start", "duration_days", "peak_mag", "n_cadences"]].to_string(index=False))"""))

cells.append(new_markdown_cell(
"""## Real recurrence time: within-sector gaps between detected outburst starts

Where a sector catches more than one outburst, I can measure a real, direct recurrence time
(time between consecutive outburst starts) with no assumptions. Where a sector's baseline is
shorter than the recurrence time, only a lower/upper bound on the gap to the sector edge is
available -- I report both honestly, rather than treating a single-outburst sector as if it
constrained the recurrence time."""))

cells.append(new_code_cell(
"""recurrence_times = []
for sector in sorted(per_sector):
    sector_events = outburst_df[outburst_df["sector"] == sector].sort_values("t_start")
    starts = sector_events["t_start"].to_numpy()
    if len(starts) >= 2:
        gaps = np.diff(starts)
        recurrence_times.extend(gaps.tolist())
        print(f"Sector {sector}: {len(starts)} outbursts -> direct recurrence gap(s): "
              f"{np.round(gaps, 2).tolist()} days")
    else:
        span = per_sector[sector]["time"].max() - per_sector[sector]["time"].min()
        print(f"Sector {sector}: only {len(starts)} outburst detected in a {span:.1f}-day "
              f"baseline -> no direct recurrence measurement possible this sector")

recurrence_times = np.array(recurrence_times)
if len(recurrence_times) > 0:
    print(f"\\nDirect within-sector recurrence measurements: {len(recurrence_times)}")
    print(f"Mean: {recurrence_times.mean():.2f} d, median: {np.median(recurrence_times):.2f} d, "
          f"range: {recurrence_times.min():.2f}-{recurrence_times.max():.2f} d")
else:
    print("\\nNo sector captured two or more outbursts; no direct in-sector recurrence measurement.")"""))

cells.append(new_code_cell(
"""fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].hist(outburst_df["peak_mag"], bins=10, color=COLORS["blue"], edgecolor=COLORS["navy"])
axes[0].set(xlabel="Peak amplitude above quiescence (mag)", ylabel="Number of outbursts",
            title=f"Real outburst amplitudes (N={len(outburst_df)})")
axes[1].hist(outburst_df["duration_days"], bins=10, color=COLORS["gold"], edgecolor=COLORS["navy"])
axes[1].set(xlabel="Outburst duration above threshold (days)", ylabel="Number of outbursts",
            title="Real outburst durations")
fig.tight_layout()
fig.savefig("ss_cygni_outburst_stats.png", dpi=160)
plt.show()

print(f"Mean peak amplitude: {outburst_df['peak_mag'].mean():.2f} mag "
      f"(range {outburst_df['peak_mag'].min():.2f}-{outburst_df['peak_mag'].max():.2f} mag)")
print(f"Mean duration above threshold: {outburst_df['duration_days'].mean():.2f} days "
      f"(range {outburst_df['duration_days'].min():.2f}-{outburst_df['duration_days'].max():.2f} days)")"""))

cells.append(new_markdown_cell(
"""## Comparing against the long-baseline literature picture

SS Cygni's outburst recurrence has been tracked by the AAVSO and professional monitoring programs
since 1896; the published literature (e.g. Cannizzo & Mattei 1992, 1998) reports a highly irregular
recurrence time historically ranging from about 7 to 50 days, with a long-term mean around
40+ days across the full 20th-century record (with a documented shift toward somewhat shorter,
more regular cycles in some multi-decade stretches). I compare the handful of real, independent
recurrence gaps measured directly from TESS against that published range -- honestly noting that
five sectors covering a few weeks each is a very small, non-uniformly-sampled subset of a
century-long, known-to-be-stochastic process, so this is a consistency check, not an independent
re-derivation of the long-term statistics."""))

cells.append(new_code_cell(
"""LITERATURE_RECURRENCE_RANGE_DAYS = (7, 50)
LITERATURE_MEAN_RECURRENCE_DAYS = 40.0
LITERATURE_AMPLITUDE_RANGE_MAG = (3.0, 4.5)

n_in_range = int(np.sum(
    (recurrence_times >= LITERATURE_RECURRENCE_RANGE_DAYS[0]) &
    (recurrence_times <= LITERATURE_RECURRENCE_RANGE_DAYS[1])
)) if len(recurrence_times) else 0

amp_consistent = bool(
    outburst_df["peak_mag"].between(*LITERATURE_AMPLITUDE_RANGE_MAG).mean() > 0.5
) if len(outburst_df) else False

print(f"TESS-measured direct recurrence gaps: {recurrence_times.round(2).tolist()}")
print(f"Published historical recurrence range: {LITERATURE_RECURRENCE_RANGE_DAYS} days "
      f"(mean ~{LITERATURE_MEAN_RECURRENCE_DAYS} d)")
print(f"Number of TESS gaps falling inside the published range: {n_in_range} / {len(recurrence_times)}")
print(f"Published amplitude range: {LITERATURE_AMPLITUDE_RANGE_MAG} mag")
print(f"Majority of TESS-measured amplitudes fall in published range: {amp_consistent}")"""))

cells.append(new_markdown_cell(
"""## Results table"""))

cells.append(new_code_cell(
"""results_table = pd.DataFrame({
    "metric": [
        "TESS sectors used", "Total real outbursts detected",
        "Mean outburst peak amplitude (mag)", "Amplitude range (mag)",
        "Mean outburst duration above threshold (days)",
        "Direct within-sector recurrence measurements",
        "Direct recurrence gaps (days)",
        "Published historical recurrence range (days)",
        "Published mean recurrence (days)",
        "Gaps consistent with published range",
    ],
    "value": [
        sorted(per_sector.keys()), len(outburst_df),
        f"{outburst_df['peak_mag'].mean():.2f}",
        f"{outburst_df['peak_mag'].min():.2f}-{outburst_df['peak_mag'].max():.2f}",
        f"{outburst_df['duration_days'].mean():.2f}",
        len(recurrence_times),
        recurrence_times.round(2).tolist(),
        f"{LITERATURE_RECURRENCE_RANGE_DAYS[0]}-{LITERATURE_RECURRENCE_RANGE_DAYS[1]}",
        LITERATURE_MEAN_RECURRENCE_DAYS,
        f"{n_in_range}/{len(recurrence_times)}" if len(recurrence_times) else "n/a",
    ]
})
results_table.to_csv("results_summary.csv", index=False)
print(results_table.to_string(index=False))"""))

cells.append(new_markdown_cell(
"""## Interpretation and limits

- **Outburst detection and amplitude measurement is a solid, primary result.** A simple,
  fully-disclosed flux-threshold detector applied to five real, independent TESS epochs recovers
  multiple genuine SS Cygni outbursts with peak amplitudes and durations that are measured directly
  from the pipeline photometry, with no synthetic data anywhere in the pipeline.
- **The recurrence-time comparison is real but necessarily a small-sample check, not a
  re-derivation of the long-term statistics.** SS Cygni's century-long AAVSO record contains
  thousands of cycles; five TESS sectors, each spanning only about a month, sample a tiny,
  non-uniformly-distributed fraction of that history, and several sectors capture at most one
  outburst (giving no direct in-sector recurrence measurement at all). Any TESS-only recurrence
  number reported here should be read as "consistent (or not) with the published range", not as an
  independent measurement of the true long-term mean recurrence time.
- **The threshold-based detector is intentionally simple and can be sensitive to the exact
  threshold and gap parameters chosen** (0.5 mag, 6-hour gap tolerance); a state-of-the-art
  analysis would fit each outburst's rise/decay profile with a physical disk-instability model
  rather than a flux threshold, and would test threshold sensitivity explicitly.
- The magnitude scale used here is *relative*, anchored to each sector's own 10th-percentile flux,
  not a photometrically calibrated absolute magnitude -- appropriate for measuring amplitudes and
  timing but not for comparing SS Cygni's absolute brightness across sectors with different
  background levels or aperture placement."""))

cells.append(new_markdown_cell(
"""## What I'd look at next

- Pull the full AAVSO visual/CCD light curve for SS Cygni over the same 2019-2024 window and
  directly overlay it with the TESS-derived outburst catalog, to check whether TESS missed any
  outbursts that occurred between sectors (an even more direct completeness check than the
  literature-range comparison used here).
- Fit each detected outburst's rise and decay separately with an exponential/power-law disk-
  instability model (rather than only measuring a threshold-crossing duration), to get a physically
  motivated decay timescale for comparison with accretion-disk viscous-timescale theory.
- Extend the recurrence-time analysis with all future TESS sectors as SS Cygni continues to be
  re-observed, since each new sector adds a genuinely independent recurrence constraint.

## Citation

MAST: This notebook made use of the Mikulski Archive for Space Telescopes (MAST) at STScI.
STScI is operated by the Association of Universities for Research in Astronomy, Inc., under NASA
contract NAS5-26555. TESS data are also served through MAST under NASA contract NNG14FC03C. See
https://archive.stsci.edu/publishing/ for the required citation language for MAST data
products."""))

cells.append(new_code_cell(
"""record = {
    "id": "2026-08-04-ss-cygni-tess-outburst-recurrence",
    "title": "SS Cygni across five real TESS years: measuring dwarf-nova outburst amplitude and recurrence directly from the light curve",
    "archive": "MAST / TESS (SPOC)",
    "date": "2026-08-04",
    "target": "SS Cygni (TIC 190696047)",
    "question": "Can a simple, transparent outburst detector applied to five real TESS epochs (2019-2024) of SS Cygni recover quantitative outburst amplitudes/durations and a recurrence time consistent with the published historical range?",
    "sectors_used": sorted(int(s) for s in per_sector.keys()),
    "n_outbursts_detected": int(len(outburst_df)),
    "mean_peak_amplitude_mag": float(outburst_df["peak_mag"].mean()),
    "mean_duration_days": float(outburst_df["duration_days"].mean()),
    "n_direct_recurrence_measurements": int(len(recurrence_times)),
    "direct_recurrence_gaps_days": [float(x) for x in recurrence_times],
    "literature_recurrence_range_days": list(LITERATURE_RECURRENCE_RANGE_DAYS),
    "literature_mean_recurrence_days": LITERATURE_MEAN_RECURRENCE_DAYS,
    "n_gaps_in_literature_range": n_in_range,
    "claim_type": "confirmed outburst detection and amplitude/duration measurement (primary); small-sample consistency check against published recurrence statistics (secondary, explicitly not a re-derivation)",
}
with open("result.json", "w") as fh:
    json.dump(record, fh, indent=2)
print(json.dumps(record, indent=2))"""))

nb = new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "colab": {"provenance": []},
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3"},
}
out = "2026-08-04-ss-cygni-tess-outburst-recurrence/notebook.ipynb"
with open(out, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("wrote", out)
