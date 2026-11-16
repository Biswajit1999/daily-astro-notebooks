"""Preregistered classical-statistics analysis of actual Euclid DR1-Foundation data.

Never loads synthetic observations; never invents missing archive rows. Run only
once the official schema/units and quality flag meaning have been reviewed.
"""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
RNG_SEED = 20261114
ZRANGES = [(0.9, 1.1), (1.1, 1.3), (1.3, 1.5)]


def prepare(df, snr_min=5, pz_min=0.99):
    """Keep transparent, sequential counts for every a priori exclusion."""
    flow = [('Retrieved joined rows', len(df))]
    if df['object_id'].duplicated(keep=False).any():
        bad = df[df['object_id'].duplicated(keep=False)].copy()
        bad.to_csv(BASE / 'tables' / 'ambiguous_duplicate_rows.csv', index=False)
        # Drop all rows of every ambiguous object, rather than pick the most
        # attractive/highest-SNR spectrum and bias the effect estimate.
        df = df[~df['object_id'].isin(bad['object_id'])].copy()
    flow.append(('Unambiguous one-row-per-object only', len(df)))
    for name, cond in [
        ('VIS-detected', lambda t: t.vis_det.eq(1)),
        ('VIS and detection flags zero', lambda t: t.flag_vis.eq(0) & t.det_quality_flag.eq(0)),
        ('Positive finite Kron radius and VIS aperture flux', lambda t: np.isfinite(t.kron_radius) & (t.kron_radius > 0) & np.isfinite(t.flux_vis_2fwhm_aper) & (t.flux_vis_2fwhm_aper > 0)),
        ('Reliable primary SPE redshift', lambda t: np.isfinite(t.spe_z) & np.isfinite(t.spe_z_prob) & (t.spe_z_prob >= pz_min) & (t.spe_z >= 0.9) & (t.spe_z <= 1.5)),
        ('Positive line flux and uncertainty', lambda t: np.isfinite(t.spe_line_flux_gf) & (t.spe_line_flux_gf > 0) & np.isfinite(t.spe_line_flux_err_gf) & (t.spe_line_flux_err_gf > 0)),
        ('Line-quality code positive', lambda t: t.spe_line_qual_gf.notna() & (t.spe_line_qual_gf > 0)),
        (f'Halpha Gaussian fit S/N >= {snr_min}', lambda t: np.isfinite(t.spe_line_snr_gf) & (t.spe_line_snr_gf >= snr_min)),
    ]:
        df = df.loc[cond(df)].copy()
        flow.append((name, len(df)))
    df['log_aperture_radius_pix'] = np.log10(df['kron_radius'].astype(float))
    df['log_halpha_flux'] = np.log10(df['spe_line_flux_gf'].astype(float))
    df['log_vis_aper_flux_uJy'] = np.log10(df['flux_vis_2fwhm_aper'].astype(float))
    return df, flow


def make_strata(df, min_cell=20):
    """Predefined z intervals; within each z interval, brightness tertiles."""
    cells = []
    for iz, (zlo, zhi) in enumerate(ZRANGES):
        sub = df[(df.spe_z >= zlo) & ((df.spe_z < zhi) if iz < 2 else (df.spe_z <= zhi))].copy()
        if len(sub) < min_cell * 3:
            continue
        # Equal-count bins; if ties prevent 3 distinct cells, omit this z-bin.
        try:
            sub['brightness_bin'] = pd.qcut(sub.log_vis_aper_flux_uJy,
                                             q=3, labels=False, duplicates='drop')
        except ValueError:
            continue
        if sub['brightness_bin'].nunique() != 3:
            continue
        for ib, block in sub.groupby('brightness_bin'):
            if len(block) < min_cell:
                continue
            middle = block.log_halpha_flux.median()
            labels = block.log_halpha_flux.to_numpy() > middle
            if labels.sum() < 10 or (~labels).sum() < 10:
                continue
            cells.append((f'z{iz}_b{int(ib)}', block, labels))
    return cells


def cell_stat(x, lab):
    return float(np.median(x[lab]) - np.median(x[~lab]))


def pooled_effect(cells, labels_override=None):
    values, weights = [], []
    for i, (_, block, labels) in enumerate(cells):
        lab = labels if labels_override is None else labels_override[i]
        values.append(cell_stat(block.log_aperture_radius_pix.to_numpy(), lab))
        weights.append(len(block))
    return float(np.average(values, weights=weights))


def test_effect(df, iterations=2000, seed=RNG_SEED):
    """Two-sided within-cell permutation and stratified two-group bootstrap."""
    cells = make_strata(df)
    analysed_n = sum(len(block) for _, block, _ in cells)
    if len(cells) < 4 or analysed_n < 200:
        return {'status': 'INCONCLUSIVE_INSUFFICIENT_CELLS',
                'cells': len(cells), 'n': analysed_n}
    rng = np.random.default_rng(seed)
    observed = pooled_effect(cells)
    null_stats, boot_stats = np.empty(iterations), np.empty(iterations)
    for b in range(iterations):
        permuted = [rng.permutation(labels) for _, _, labels in cells]
        null_stats[b] = pooled_effect(cells, permuted)
        eff, weights = [], []
        for _, block, labels in cells:
            radii = block.log_aperture_radius_pix.to_numpy()
            high = radii[labels]; low = radii[~labels]
            hi_boot = rng.choice(high, len(high), replace=True)
            lo_boot = rng.choice(low, len(low), replace=True)
            eff.append(float(np.median(hi_boot) - np.median(lo_boot)))
            weights.append(len(block))
        boot_stats[b] = np.average(eff, weights=weights)
    low, high = np.percentile(boot_stats, [2.5, 97.5])
    pval = (1 + int(np.sum(np.abs(null_stats) >= abs(observed)))) / (iterations + 1)
    return {'status': 'COMPUTED', 'cells': len(cells), 'n': analysed_n,
            'weighted_median_log10_radius_difference': observed,
            'ratio_of_aperture_radius_proxies': 10 ** observed,
            'bootstrap_95_interval_log10': [float(low), float(high)],
            'permutation_two_sided_p': float(pval),
            'iterations': iterations, 'random_seed': seed}


def plots(df, result, flow):
    (BASE / 'figures').mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'savefig.dpi': 300})
    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.scatter(df.ra, df.dec, s=3, alpha=.32, rasterized=True)
    ax.set(xlabel='Right ascension (deg)', ylabel='Declination (deg)',
           title='Euclid DR1-F | EDF-N Hα sample (post quality cuts)')
    ax.invert_xaxis(); fig.tight_layout()
    fig.savefig(BASE/'figures'/'day01_skymap.png'); fig.savefig(BASE/'figures'/'day01_skymap.svg'); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.scatter(df.spe_z, df.log_halpha_flux, s=5, alpha=.3, rasterized=True)
    ax.set(xlabel='SPE spectroscopic redshift',
           ylabel=r'log$_{10}$(Hα line flux / [erg s$^{-1}$ cm$^{-2}$])',
           title='Detected Hα sample: flux–redshift selection (not completeness-corrected)')
    fig.tight_layout()
    fig.savefig(BASE/'figures'/'day01_halpha_vs_redshift.png'); fig.savefig(BASE/'figures'/'day01_halpha_vs_redshift.svg'); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    ax.scatter(df.log_halpha_flux, df.log_aperture_radius_pix, s=5, alpha=.25, rasterized=True)
    ax.set(xlabel=r'log$_{10}$(Hα line flux / [erg s$^{-1}$ cm$^{-2}$])',
           ylabel=r'log$_{10}$(MER Kron aperture semi-major radius / pixel)',
           title='Raw association only (unadjusted; not a physical half-light radius)')
    fig.tight_layout()
    fig.savefig(BASE/'figures'/'day01_raw_relation.png'); fig.savefig(BASE/'figures'/'day01_raw_relation.svg'); plt.close(fig)

    if result.get('status') == 'COMPUTED':
        effect = result['weighted_median_log10_radius_difference']
        lo, hi = result['bootstrap_95_interval_log10']
        fig, ax = plt.subplots(figsize=(6.4, 3.4))
        ax.axvline(0, color='0.5', linestyle='--', linewidth=1)
        ax.errorbar(effect, 0, xerr=[[effect-lo], [hi-effect]],
                    fmt='o', capsize=5)
        ax.set(yticks=[0], yticklabels=['Stratified high–low Hα'],
               xlabel=r'Weighted difference in median log$_{10}$(Kron radius / pixel)',
               title='Predefined conditional statistic and bootstrap 95% interval')
        ax.set_ylim(-0.7, 0.7); fig.tight_layout()
        fig.savefig(BASE/'figures'/'day01_primary_effect.png')
        fig.savefig(BASE/'figures'/'day01_primary_effect.svg')
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    labels, counts = zip(*flow)
    ax.plot(range(len(counts)), counts, 'o-')
    ax.set_xticks(range(len(labels)), [f'{i+1}' for i in range(len(labels))])
    ax.set(xlabel='Pre-registered selection step (see tables/day01_selection_flow.csv)',
           ylabel='Number of catalogue rows', title='Sample attrition')
    fig.tight_layout()
    fig.savefig(BASE/'figures'/'day01_selection_flow.png'); plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm-units-checked', action='store_true')
    parser.add_argument('--confirm-flags-checked', action='store_true')
    args = parser.parse_args()
    if not (args.confirm_units_checked and args.confirm_flags_checked):
        raise SystemExit('NO-GO: verify metadata and DR1 flag semantics first; then pass both confirmations.')
    raw_path = BASE/'tables'/'day01_raw_irsa.csv'
    manifest_path = BASE/'metadata'/'fetch_manifest.json'
    if not raw_path.is_file() or not manifest_path.is_file():
        raise SystemExit('NO-GO: missing actual IRSA archive data or fetch manifest. No synthetic fallback.')
    manifest = json.loads(manifest_path.read_text())
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    if raw_hash != manifest['hashes']['raw_csv_sha256']:
        raise SystemExit('NO-GO: downloaded input hash has changed.')
    df = pd.read_csv(raw_path, dtype={'object_id': 'int64'}, low_memory=False)
    required = ['object_id', 'ra', 'dec', 'vis_det', 'kron_radius',
                'flux_detection_total', 'flux_vis_2fwhm_aper', 'flag_vis', 'det_quality_flag',
                'spe_z', 'spe_z_prob', 'spe_line_qual_gf',
                'spe_line_snr_gf', 'spe_line_flux_gf', 'spe_line_flux_err_gf']
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise SystemExit(f'NO-GO: missing actual archive columns {missing}')
    selected, flow = prepare(df)
    pd.DataFrame(flow, columns=['selection_step', 'remaining_rows']).to_csv(BASE/'tables'/'day01_selection_flow.csv', index=False)
    if len(selected) < 200:
        raise SystemExit(f'INCONCLUSIVE: only {len(selected)} Hα detections after cuts. See selection flow.')
    selected.to_csv(BASE/'tables'/'day01_selected_derived.csv', index=False)
    main_result = test_effect(selected)
    cell_rows = []
    for cellname, block, upper in make_strata(selected):
        logr = block.log_aperture_radius_pix.to_numpy()
        cell_rows.append({'stratum': cellname, 'n': len(block),
                          'n_high_Halpha': int(upper.sum()),
                          'n_low_Halpha': int((~upper).sum()),
                          'median_log_radius_high': float(np.median(logr[upper])),
                          'median_log_radius_low': float(np.median(logr[~upper])),
                          'difference_log10_radius': cell_stat(logr, upper)})
    pd.DataFrame(cell_rows).to_csv(BASE/'tables'/'day01_cell_statistics.csv', index=False)
    strong, _ = prepare(df, snr_min=10, pz_min=0.99)
    reliable, _ = prepare(df, snr_min=5, pz_min=0.999)
    # A second test changes z limits without redefining the bright/weak split.
    centered = selected[(selected.spe_z >= .95) & (selected.spe_z <= 1.45)].copy()
    result = {'date': '2026-11-14', 'data_release': 'DR1-Foundation',
              'archive_query_utc': manifest['query_utc'],
              'units_and_flags_confirmed_by_operator': True,
              'measurement_type': 'MER Kron aperture radius in pixels (not half-light radius)',
              'scope': 'Detected Halpha emitters only, not a complete galaxy population',
              'n_retrieved': len(df), 'n_selected': len(selected),
              'primary': main_result,
              'robustness': {'SNR_at_least_10': test_effect(strong),
                             'spe_z_prob_at_least_0.999': test_effect(reliable),
                             'restricted_redshift_0.95_to_1.45': test_effect(centered)},
              'readiness': 'INTERPRETATION_PENDING_IMAGE_INSPECTION_AND_LITERATURE_RECHECK',
              'software': {'python': platform.python_version(), 'numpy': np.__version__,
                           'pandas': pd.__version__, 'matplotlib': matplotlib.__version__},
              'input_sha256': raw_hash,
              'limits': ['Flux-limited selected emitters, not nondetections',
                         'No completeness, PSF or physical-size correction',
                         'Kron radius is a photometric aperture semi-major axis',
                         'Nearby blends and NISP line confusion require inspection']}
    plots(selected, main_result, flow)
    (BASE/'tables'/'day01_analysis_summary.json').write_text(json.dumps(result, indent=2))
    selected[['object_id','ra','dec','spe_z','spe_line_snr_gf','kron_radius']].sort_values('object_id').iloc[::max(1, len(selected)//12)].head(12).to_csv(BASE/'tables'/'day01_inspection_candidates.csv', index=False)
    print(json.dumps(result, indent=2))
    print('Still NO-GO for LinkedIn until inspected images/spectra and repeated literature audit.')

if __name__ == '__main__':
    main()
