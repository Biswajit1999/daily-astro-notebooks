"""Summarise tile coverage and imaging-flag effects in the archived Day 1 pilot."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULTS = Path(__file__).resolve().parents[1] / 'real_results'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=RESULTS)
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    cols = {'object_id': str}
    selected = pd.read_csv(RESULTS / 'selected_426.csv', dtype=cols)
    matched = pd.read_csv(RESULTS / 'size_matched_327.csv', dtype=cols)
    clean = pd.read_csv(RESULTS / 'strict_quality_150.csv', dtype=cols)
    excluded = matched.loc[~matched.object_id.isin(clean.object_id)]
    coverage = selected.groupby('tileid').size()
    groups = {'selected': selected, 'size_matched': matched,
              'unmatched': selected.loc[~selected.object_id.isin(matched.object_id)],
              'quality_passing': clean, 'excluded_after_matching': excluded}
    data = {
        'definitions': {'flux_Halpha': '10^-16 erg/s/cm^2', 'flux_VIS': 'microJy',
                        'Kron_radius': 'pixels'},
        'tile_counts': {str(k): int(v) for k, v in coverage.items()},
        'matched_cut_failures_overlapping': {
            'nonzero_VIS_flag': int(matched.flag_vis.ne(0).sum()),
            'nonzero_detection_quality_flag': int(matched.det_quality_flag.ne(0).sum()),
            'spurious_probability_at_least_0_5': int(matched.spurious_prob.ge(.5).sum()),
        },
        'groups': {name: {
            'n': len(rows), 'median_z': float(rows.spe_z.median()),
            'median_Halpha': float(rows.ha_flux.median() * 1e16),
            'median_VIS': float(rows.flux_vis_2fwhm_aper.median()),
            'median_Kron': float(rows.kron_radius.median()) if 'kron_radius' in rows else None,
        } for name, rows in groups.items()},
    }
    (output / 'selection_diagnostics.json').write_text(json.dumps(data, indent=2) + '\n')

    fig, (tiles, kron) = plt.subplots(1, 2, figsize=(8.5, 3.1), layout='constrained')
    bars = tiles.barh([str(tile) for tile in coverage.index], coverage, color='#9aa4ae')
    bars[list(coverage.index).index(101834044)].set_color('#256779')
    tiles.bar_label(bars, padding=4, fontsize=8)
    tiles.set(xlim=(0, 380), xlabel='Selected Hα sources', ylabel='MER tile', title='a. Morphology coverage')
    kron.hist([clean.kron_radius, excluded.kron_radius], bins=22, density=True, histtype='step',
              lw=1.7, color=['#256779', '#995224'], label=['Pass (150)', 'Excluded (177)'])
    kron.legend(frameon=False, fontsize=8)
    kron.set(xlabel='MER Kron radius (pixels)', ylabel='Density', title='b. Effect of imaging cuts')
    for ax in (tiles, kron):
        ax.spines[['top', 'right']].set_visible(False)
    fig.savefig(output / 'selection_diagnostics.png', dpi=155)
    plt.close(fig)


if __name__ == '__main__':
    main()
