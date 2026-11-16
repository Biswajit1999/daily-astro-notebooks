"""Compare five Euclid VIS stamps and their Hα and [O III] spectral windows."""
import argparse
from pathlib import Path

from astropy.io import fits
from astropy.wcs import WCS
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from audit_grism_halpha import DAY02, fit_window

TARGETS = DAY02 / 'targets'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=TARGETS)
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    targets = pd.read_csv(TARGETS / 'five_targets.csv', dtype={'object_id': str})
    spectra = pd.read_csv(TARGETS / 'five_spectra.csv.gz', dtype={'object_id': str})
    if len(targets) != 5 or targets.object_id.duplicated().any():
        raise ValueError('Expected five distinct objects')
    diagnostics = []
    fig, axes = plt.subplots(5, 3, figsize=(9, 9.2), layout='constrained',
                             gridspec_kw={'width_ratios': [1, 2, 2]})
    with fits.open(TARGETS / 'five_vis.fits.gz') as images:
        for index, (target, plot_row) in enumerate(zip(targets.itertuples(), axes, strict=True)):
            image, *panels = plot_row
            hdu = images[target.label]
            x, y = WCS(hdu.header).world_to_pixel_values(target.ra_deg, target.dec_deg)
            lo, hi = np.nanpercentile(hdu.data, (13, 99.4))
            image.imshow(np.arcsinh(5 * (hdu.data-lo)/(hi-lo)), origin='lower', cmap='gray')
            image.scatter(x, y, s=46, marker='+', c='#f7b365')
            image.plot([3, 13], [4, 4], color='white', lw=1.2)
            image.set_xticks([])
            image.set_yticks([])
            image.set_ylabel(f'{target.label}   {target.object_id}', fontsize=7.3)
            lines = [('BGS' if target.label == 'E' else 'RGS', 'Hα region', 6564.61),
                     ('BGS', '[O III] λ5008', 5008.24)]
            for ax, (grism, name, rest) in zip(panels, lines, strict=True):
                data = spectra[(spectra.object_id == target.object_id) & (spectra.grism == grism)]
                centre = rest * (1 + target.spe_z)
                strict, window = fit_window(data, centre)
                fallback = False
                if strict['status'] != 'fitted':
                    relaxed, candidate = fit_window(data, centre, allow_low_snr=True)
                    if relaxed['status'] == 'fitted':
                        fit, window, fallback = relaxed, candidate, True
                    else:
                        fit = strict
                else:
                    fit = strict
                snr = fit.get('sigma_30A_formal_snr')
                adjusted = snr / max(1, fit['sigma_30A_sideband_rms']) if snr is not None else None
                diagnostics.append(dict(label=target.label, object_id=target.object_id, grism=grism,
                                        feature=name, centre_A=centre, strict_status=strict['status'],
                                        fit_mask='allow_mask_2' if fallback else 'strict',
                                        formal_snr=snr, adjusted_snr=adjusted))
                dx = window.wavelength - centre
                valid = window.usable
                ax.plot(dx, window.signal.where(window.ndith > 0), color='.64', lw=.8)
                ax.scatter(dx[valid], window.signal[valid], s=7, color='#256779')
                if 'model' in window:
                    ax.plot(dx, window.model, lw=1, color='#256779')
                if fallback:
                    warning = valid & window['mask'].eq(2)
                    ax.scatter(dx[warning], window.signal[warning], s=14, marker='x', color='#995224')
                badge = 'No usable fit' if adjusted is None else f'Adj. S/N {adjusted:.1f}'
                if fallback:
                    badge += ' (mask 2 included)'
                ax.text(.02, .96, f'{grism} · {badge}', transform=ax.transAxes, va='top', fontsize=7.2,
                        bbox={'facecolor':'white','edgecolor':'none','alpha':.88,'pad':1.5})
                ax.axvline(0, color='.35', lw=.8, ls=':')
                ax.set_xlim(-250, 250)
                ax.tick_params(labelsize=7)
                if index == 0:
                    ax.set_title(name, fontsize=10)
                if index < len(targets)-1:
                    ax.set_xticklabels([])
                else:
                    ax.set_xlabel('Offset from SPE prediction (Å)', fontsize=8)
    axes[0,0].set_title('Euclid VIS', fontsize=10)
    fig.savefig(output / 'five_source_diagnostics.png', dpi=155)
    pd.DataFrame(diagnostics).to_csv(output / 'five_source_fits.csv', index=False, float_format='%.9g')
    plt.close(fig)


if __name__ == '__main__':
    main()
