"""Download a bounded Euclid DR1-Foundation H-alpha catalogue sample from IRSA.

No synthetic data. Refuses to proceed when DR1 schema cannot be checked.
Run from the day01 directory: python scripts/fetch_day01.py
"""
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
QUERY = HERE / 'queries' / 'day01_sample.adql'
RAW = HERE / 'tables' / 'day01_raw_irsa.csv'

REQUIRED = {
    'euclid_dr1_mer_catalogue_deep_survey': [
        'object_id', 'ra', 'dec', 'tileid', 'vis_det', 'kron_radius',
        'flux_detection_total', 'flux_vis_2fwhm_aper', 'flag_vis', 'det_quality_flag', 'spurious_prob'],
    'euclid_dr1_spectro_z_spe_galaxy_candidates_deep': [
        'object_id', 'spe_rank', 'spe_z', 'spe_z_prob'],
    'euclid_dr1_spectro_line_features_spe_line_features_deep': [
        'object_id', 'spe_rank', 'spe_line_name', 'spe_line_qual_gf',
        'spe_line_snr_gf', 'spe_line_flux_gf', 'spe_line_flux_err_gf',
        'spe_line_central_wl_gf'],
}

def metadata_rows(table):
    """Extract the names and raw metadata from the public IRSA column listing."""
    cols = [str(c) for c in table.colnames]
    key = next((c for c in cols if c.lower() in ('name', 'column_name', 'column')), None)
    if key is None:
        raise RuntimeError(f'Unrecognised IRSA column metadata format: {cols}')
    rows = []
    for r in table:
        rows.append({c: (None if r[c] is None else str(r[c])) for c in cols})
    return {str(row[key]).lower() for row in rows}, rows

def main():
    from astroquery.ipac.irsa import Irsa
    from importlib.metadata import version
    HERE.joinpath('metadata').mkdir(exist_ok=True)
    schema = {}
    for name, needed in REQUIRED.items():
        tab = Irsa.list_columns(catalog=name, full=True)
        observed, rows = metadata_rows(tab)
        missing = sorted(set(needed) - observed)
        schema[name] = {'required_columns': needed, 'column_metadata': rows,
                        'missing_columns': missing}
        if missing:
            dest = HERE / 'metadata' / 'schema_snapshot.json'
            dest.write_text(json.dumps(schema, indent=2))
            raise RuntimeError(f'DR1 schema mismatch in {name}: {missing}; saved {dest}')
    (HERE / 'metadata' / 'schema_snapshot.json').write_text(json.dumps(schema, indent=2))
    sql = QUERY.read_text()
    # Execute the versioned ADQL exactly as committed. A server error is not
    # permission to silently substitute Q1 tables or drop fields.
    data = Irsa.query_tap(sql, async_job=True).to_table()
    if not len(data):
        raise RuntimeError('Query returned zero rows. No analysis is possible.')
    data.to_pandas().to_csv(RAW, index=False)
    hashes = {'adql_sha256': hashlib.sha256(sql.encode()).hexdigest(),
              'raw_csv_sha256': hashlib.sha256(RAW.read_bytes()).hexdigest()}
    manifest = {'release': 'Euclid DR1-Foundation', 'query_utc': datetime.now(timezone.utc).isoformat(),
                'archive': 'IRSA TAP/ADQL', 'tables': list(REQUIRED),
                'n_rows': len(data), 'runtime': platform.python_version(),
                'astroquery_version': version('astroquery'), 'hashes': hashes,
                'units_review': 'PENDING_HUMAN_VERIFICATION',
                'flag_semantics_review': 'PENDING_HUMAN_VERIFICATION'}
    (HERE / 'metadata' / 'fetch_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Saved {len(data)} unfiltered archive rows to {RAW}.')
    print('STOP: inspect metadata/schema_snapshot.json, verify field definitions, units and flags.')
    print('Only then run analyse_day01.py with both explicit confirmations.')

if __name__ == '__main__':
    main()
