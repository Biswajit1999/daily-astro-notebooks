"""Tests of analysis mechanics only. No synthetic observations or science plots."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'analyse_day01.py'
spec = importlib.util.spec_from_file_location('day01_stats', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_median_direction_and_zero():
    vals = np.array([1., 1., 2., 2.])
    labs = np.array([False, False, True, True])
    assert m.cell_stat(vals, labs) == 1.
    assert m.cell_stat(np.ones(4), labs) == 0.


def test_insufficient_sample_is_inconclusive():
    empty = pd.DataFrame({'spe_z': [], 'log_detection_flux_uJy': [],
                          'log_vis_aper_flux_uJy': [], 'log_halpha_flux': [],
                          'log_aperture_radius_pix': []})
    result = m.test_effect(empty, iterations=3)
    assert result['status'] == 'INCONCLUSIVE_INSUFFICIENT_CELLS'


def test_repeated_halpha_fits_are_combined_by_exact_id():
    identity = 2697974927659867240
    lines = pd.DataFrame({
        'object_id': [identity, identity, identity, identity, identity + 1, identity + 1],
        'spe_rank': [0, 0, 0, 1, 0, 0],
        'spe_line_name': ['Halpha', 'Halpha', 'Halpha', 'Halpha', 'Hbeta', 'Halpha'],
        'spe_line_flux_gf': [1., 3., -999., 99., 4., 5.],
        'spe_line_flux_err_gf': [0.1] * 6,
        'spe_line_snr_gf': [10., 30., 20., 25., 15., 50.],
        'spe_line_central_wl_gf': [13000.] * 6,
    })
    result = m.aggregate_halpha_fits(lines).set_index('object_id')
    assert result.index.tolist() == [identity, identity + 1]
    assert result.ha_flux.tolist() == [2., 5.]
    assert result.n_line_entries.tolist() == [2, 1]
