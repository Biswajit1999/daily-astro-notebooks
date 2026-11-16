"""Compare fixed-centre H-alpha-region fits in the DR1 NISP overlap."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DAY = Path(__file__).resolve().parent
DAY2 = DAY.parents[1] / '2026-11-15-day02' / 'analysis'
sys.path.insert(0, str(DAY2 / 'scripts'))
from audit_grism_halpha import fit_window, get_hats_spectrum  # noqa: E402
from screen_interesting_objects import read_subset  # noqa: E402

REST = 6564.61
OFFSETS = (-440, -300, 0, 300, 440)
WIDTH = 'sigma_30A'
GRISMS = ('BGS', 'RGS')


def fits(spectrum, centre, allow_warning=False):
    wav = spectrum.wavelength.to_numpy()
    if centre - 250 < wav.min() or centre + 250 > wav.max():
        return {'status': 'window_truncated'}
    fit, _ = fit_window(spectrum, centre, allow_low_snr=allow_warning)
    status = {'status': fit['status'], 'core': fit['usable_core'],
              'core_warning': fit['core_bins_masked_low_snr_only'],
              'left': fit['usable_blue_sideband'], 'right': fit['usable_red_sideband']}
    if fit['status'] != 'fitted':
        return status
    err = fit[f'{WIDTH}_flux_se_1e16'] * max(1, fit[f'{WIDTH}_sideband_rms'])
    flux = fit[f'{WIDTH}_flux_1e16']
    return {**status, 'flux': flux, 'error': err, 'snr': flux / err}


def describe(rows):
    usable = rows.both_fit
    g = rows.loc[usable]
    blue = g.BGS_snr.ge(5)
    red = g.RGS_snr.ge(5)
    both = g.loc[blue & red]
    ratios = np.log10(both.RGS_flux / both.BGS_flux)
    return {
        'geometric_overlap': len(rows), 'both_fit': int(usable.sum()),
        'fit_blue_only': int((rows.BGS_status.eq('fitted') & rows.RGS_status.ne('fitted')).sum()),
        'fit_red_only': int((rows.RGS_status.eq('fitted') & rows.BGS_status.ne('fitted')).sum()),
        'blue_fit_all': int(rows.BGS_status.eq('fitted').sum()),
        'red_fit_all': int(rows.RGS_status.eq('fitted').sum()),
        'blue_above_5_all': int(rows.BGS_snr.ge(5).sum()),
        'red_above_5_all': int(rows.RGS_snr.ge(5).sum()),
        'both_above_5': len(both), 'blue_only_above_5': int((blue & ~red).sum()),
        'red_only_above_5': int((red & ~blue).sum()), 'neither_above_5': int((~(blue | red)).sum()),
        'both_below_minus_5': int((g.BGS_snr.le(-5) & g.RGS_snr.le(-5)).sum()),
        'both_above_5_log_ratio_median': float(ratios.median()) if len(both) else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=DAY)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    pilot = pd.read_csv(DAY2 / 'observed_results/all_morphology_matched.csv.gz')
    desi = pd.read_csv(DAY2 / 'validation/desi_pairs.csv')
    desi = desi.loc[desi.separation_arcsec.le(0.2)]
    unique = ~desi.object_id.duplicated(keep=False) & ~desi.targetid.duplicated(keep=False)
    desi = desi.loc[unique & desi.spectype.eq('GALAXY')].set_index('object_id')
    rows, products = read_subset(args.cache, pilot)
    expected = pilot.set_index('object_id')
    tile_rows = rows[['object_id','tileid','lrange']]
    if tile_rows.duplicated().any() or not (tile_rows.groupby('object_id').size() == 2).all():
        raise ValueError('Expected one spectrum per object and grism')
    observations = []
    nominal_overlap = 0
    for oid in sorted(rows.object_id.unique()):
        target = expected.loc[oid]
        spectra = {g: get_hats_spectrum(rows, oid, target.tileid, g)[0] for g in GRISMS}
        if any(s is None for s in spectra.values()):
            raise ValueError(f'Spectrum missing for {oid}')
        lo = max(s.wavelength.min() for s in spectra.values())
        hi = min(s.wavelength.max() for s in spectra.values())
        centre = REST * (1 + target.spe_z)
        nominal_overlap += lo <= centre <= hi
        if not lo + 250 <= centre <= hi - 250:
            continue
        for offset in OFFSETS:
            if not lo + 250 <= centre + offset <= hi - 250:
                continue
            row = {'object_id': int(oid), 'tileid': int(target.tileid), 'offset_A': offset,
                   'centre_A': centre + offset, 'spe_z': target.spe_z, 'ra': target.ra,
                   'dec': target.dec, 'clean': target.flag_vis == 0 and target.det_quality_flag == 0 and target.spurious_prob < .5}
            if oid in desi.index:
                match = desi.loc[oid]
                row.update(desi_z=match.z, desi_sep_arcsec=match.separation_arcsec,
                           desi_delta_z_norm=match.delta_z_norm)
            for grism, spectrum in spectra.items():
                row.update({f'{grism}_{key}': value for key, value in fits(spectrum, centre + offset).items()})
            if offset == 0:
                for grism, spectrum in spectra.items():
                    row.update({f'warning_{grism}_{key}': value for key, value in fits(spectrum, centre, True).items()})
            observations.append(row)
    full = pd.DataFrame(observations)
    full['both_fit'] = full.BGS_status.eq('fitted') & full.RGS_status.eq('fitted')
    signal = full.loc[full.offset_A.eq(0)].copy()
    warning = signal.filter(regex=r'^warning_[BR]GS_').rename(columns=lambda x: x.removeprefix('warning_'))
    warning['both_fit'] = warning.BGS_status.eq('fitted') & warning.RGS_status.eq('fitted')
    warning.insert(0, 'object_id', signal.object_id)
    warning.insert(1, 'desi_z', signal.desi_z)
    warning.insert(2, 'clean', signal.clean)
    warning_candidates = warning.loc[warning.BGS_snr.ge(5) & warning.RGS_snr.ge(5)]
    common_ids = full.groupby('object_id').filter(lambda df: len(df)==len(OFFSETS) and df.both_fit.all()).object_id.unique()
    common = full[full.object_id.isin(common_ids)]
    paired = signal[signal.both_fit]
    candidates = paired[paired.BGS_snr.ge(5) & paired.RGS_snr.ge(5)].copy()
    candidates['log10_red_blue'] = np.log10(candidates.RGS_flux / candidates.BGS_flux)
    candidates['combined_discrepancy'] = (candidates.RGS_flux - candidates.BGS_flux) / np.hypot(candidates.RGS_error, candidates.BGS_error)
    candidates['min_snr'] = candidates[['BGS_snr','RGS_snr']].min(axis=1)
    candidates = candidates.sort_values('min_snr', ascending=False)
    stable = []
    for target in candidates.itertuples(index=False):
        offsets = {}
        for grism in GRISMS:
            spec, count = get_hats_spectrum(rows, target.object_id, target.tileid, grism)
            assert count == 1
            fit, _ = fit_window(spec, target.centre_A)
            offsets[grism] = min(fit[f'sigma_{width}A_formal_snr'] / max(1, fit[f'sigma_{width}A_sideband_rms']) for width in (20, 30, 45))
        stable.append(min(offsets.values()) >= 5)
    candidates['all_widths_both_5'] = stable
    stress = []
    for candidate in warning_candidates.itertuples(index=False):
        source = expected.loc[candidate.object_id]
        centre = REST * (1 + source.spe_z)
        red, _ = get_hats_spectrum(rows, candidate.object_id, source.tileid, 'RGS')
        _, red_window = fit_window(red, centre, allow_low_snr=True)
        core = red_window.loc[red_window.usable & (red_window.wavelength - centre).abs().le(45)]
        peak = (core.signal - core.continuum).idxmax()
        peak_wavelength = float(core.loc[peak, 'wavelength'])
        modified = red.assign(mask=red['mask'].where(red.wavelength.ne(peak_wavelength), 1))
        reduced = fits(modified, centre, True)
        record = {'object_id': int(candidate.object_id), 'tileid': int(source.tileid),
                  'red_peak_mask': int(core.loc[peak, 'mask']), 'red_peak_A': peak_wavelength,
                  'red_reduced_status': reduced['status'], 'red_reduced_snr': reduced.get('snr'),
                  'warning_blue_snr': candidate.BGS_snr, 'warning_red_snr': candidate.RGS_snr,
                  'desi_z': candidate.desi_z}
        if pd.notna(candidate.desi_z):
            blue, _ = get_hats_spectrum(rows, candidate.object_id, source.tileid, 'BGS')
            for grism, spectrum in (('blue', blue), ('red', red)):
                result = fits(spectrum, REST * (1 + candidate.desi_z), True)
                record[f'desi_centre_{grism}_snr'] = result.get('snr')
        stress.append(record)
    stress_columns = ['object_id', 'tileid', 'red_peak_mask', 'red_peak_A', 'red_reduced_status',
                      'red_reduced_snr', 'warning_blue_snr', 'warning_red_snr', 'desi_z',
                      'desi_centre_blue_snr', 'desi_centre_red_snr']
    stress = pd.DataFrame(stress, columns=stress_columns)
    summary = {'paired_parent': int(rows.object_id.nunique()), 'nominal_centre_overlap': int(nominal_overlap),
               'real_line': describe(signal), 'warning_inclusive_real_line': describe(warning),
               'red_strict_core_lt_5': int(signal.RGS_core.lt(5).sum()),
               'red_strict_either_sideband_lt_5': int((signal[['RGS_left','RGS_right']].min(axis=1) < 5).sum()),
               'warning_dual_clean_imaging': int(warning_candidates.clean.sum()),
               'red_strict_zero_core': int(signal.RGS_core.eq(0).sum()),
               'strict_blue_above_5_with_desi_galaxy': int((signal.BGS_snr.ge(5) & signal.desi_z.notna()).sum()),
               'warning_dual_brightest_red_bin_test': {
                   'remains_above_5': int(stress.red_reduced_snr.ge(5).sum()),
                   'fit_below_5': int(stress.red_reduced_snr.lt(5).sum()),
                   'coverage_failure': int(stress.red_reduced_status.ne('fitted').sum()),
                   'independent_desi_galaxy_matches': int(stress.desi_z.notna().sum()),
                   'above_5_both_at_desi_centre': int((stress.desi_centre_blue_snr.ge(5) & stress.desi_centre_red_snr.ge(5)).sum()),
                   'above_5_both_at_desi_centre_and_red_peak_removal': int((stress.desi_centre_blue_snr.ge(5) & stress.desi_centre_red_snr.ge(5) & stress.red_reduced_snr.ge(5)).sum()),
               },
               'warning_dual_object_ids': [str(x) for x in warning_candidates.object_id], 'other_centres': {str(k):describe(g) for k,g in full.groupby('offset_A',sort=True) if k},
               'common_sources_all_offsets': len(common_ids), 'common_source_results': {str(k):describe(g) for k,g in common.groupby('offset_A',sort=True)},
               'both_above_5_all_widths': sum(stable), 'dual_within_half_dex': int(candidates.log10_red_blue.abs().le(.5).sum()),
               'desi_galaxies_within_0_2arcsec_dual': int(candidates.desi_z.notna().sum()),
               'input_products': products}
    for name in ('observed_results/all_morphology_matched.csv.gz','validation/desi_pairs.csv'):
        summary.setdefault('catalogue_inputs_sha256',{})[name] = hashlib.sha256((DAY2/name).read_bytes()).hexdigest()
    (args.output / 'overlap_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    full.to_csv(args.output/'overlap_fits.csv.gz',index=False,float_format='%.10g',compression={'method':'gzip','mtime':0})
    stress.to_csv(args.output/'peak_removal.csv',index=False,float_format='%.10g')
    warning_candidates.to_csv(args.output/'warning_sensitivity_candidates.csv',index=False,float_format='%.10g')
    candidates.to_csv(args.output/'dual_grism_candidates.csv',index=False,float_format='%.10g')
    print(json.dumps(summary,indent=2))

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.25), layout='constrained')
    ax = axes[0]
    stages = ['Wavelength overlap', 'Strict blue fit', 'Strict red fit', 'Both strict fits',
              'Both fits allowing mask 2']
    counts = [len(signal), summary['real_line']['blue_fit_all'], summary['real_line']['red_fit_all'],
              len(paired), int(warning.both_fit.sum())]
    bars = ax.barh(stages[::-1], counts[::-1], color=['#8e9ba4', '#326d81', '#326d81', '#326d81', '#b37441'])
    ax.bar_label(bars, padding=4, fontsize=8)
    ax.set(xlim=(0, max(counts)*1.16), xlabel='Number of sources', title='a. Geometric and usable overlap')
    ax = axes[1]
    for column, label, color in [('BGS_core','Blue grism','#326d81'), ('RGS_core','Red grism','#b37441')]:
        count = signal[column].fillna(0).value_counts().sort_index()
        ax.step(count.index, count.values, where='mid', lw=1.5, label=label, color=color)
    ax.axvline(5, color='.4', ls=':', lw=1)
    ax.legend(frameon=False, fontsize=8)
    ax.set(xlabel='Strict usable core pixels', ylabel='Number of sources', title='b. Fit-core coverage')
    fig.savefig(args.output/'overlap_diagnostics.png',dpi=160)
    plt.close(fig)

    # Show the strongest peak-removal survivor and the strongest dual DESI-centred fit.
    confirmed = stress.dropna(subset=['desi_centre_blue_snr', 'desi_centre_red_snr'])
    survivors = stress.loc[stress.red_reduced_snr.ge(5)]
    if survivors.empty or confirmed.empty:
        return
    first = survivors.sort_values('red_reduced_snr', ascending=False).iloc[0]
    second = confirmed.loc[confirmed[['desi_centre_blue_snr', 'desi_centre_red_snr']].min(axis=1).idxmax()]
    fig, axes = plt.subplots(2, 2, figsize=(7.5, 4.2), layout='constrained')
    for index, (example, panels) in enumerate(zip((first, second), axes, strict=True)):
        oid = int(example.object_id)
        source = expected.loc[oid]
        centre = REST * (1 + (source.spe_z if index == 0 else example.desi_z))
        for grism, ax in zip(GRISMS, panels, strict=True):
            spec, _ = get_hats_spectrum(rows, oid, source.tileid, grism)
            fit, window = fit_window(spec, centre, allow_low_snr=True)
            good = window.usable
            masks = window['mask'].eq(2) & good
            dx = window.wavelength - centre
            ax.plot(dx, window.signal.where(window.ndith.gt(0)), color='.70', lw=.8)
            ax.scatter(dx[good & ~masks], window.signal[good & ~masks], s=13, c='#326d81')
            ax.scatter(dx[masks], window.signal[masks], s=22, marker='x', c='#a96031')
            if fit['status'] == 'fitted':
                ax.plot(dx, window.model, color='#326d81', lw=1)
            if index == 0 and grism == 'RGS':
                ax.axvline(example.red_peak_A-centre, ls='--', lw=1, c='#a96031')
            ax.axvline(0, ls=':', color='.35', lw=1)
            ax.set(title=f'{oid} · {grism}', xlim=(-250,250))
            if index == 1:
                ax.set_xlabel('Offset from adopted Hα centre (Å)')
    fig.supylabel('Flux density (10⁻¹⁶ erg s⁻¹ cm⁻² Å⁻¹)')
    fig.savefig(args.output/'example_spectra.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
