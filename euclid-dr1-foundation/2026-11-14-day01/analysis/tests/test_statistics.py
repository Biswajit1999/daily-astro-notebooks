"""Tests of analysis mechanics only. No synthetic observations or science plots."""
import importlib.util
from pathlib import Path
import numpy as np

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
    import pandas as pd
    empty = pd.DataFrame({'spe_z': [], 'log_detection_flux_uJy': [],
                          'log_vis_aper_flux_uJy': [], 'log_halpha_flux': [],
                          'log_aperture_radius_pix': []})
    result = m.test_effect(empty, iterations=3)
    assert result['status'] == 'INCONCLUSIVE_INSUFFICIENT_CELLS'
