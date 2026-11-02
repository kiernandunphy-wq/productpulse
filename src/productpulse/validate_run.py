"""Compare real BigQuery aggregates with foundation outputs; do not infer cloud success locally."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def compare_funnel(sql, directory):
    pairs = [('ALL', 'ordered_funnel.csv'), ('DEVICE', 'device_funnel.csv')]
    for scope, filename in pairs:
        expected = pd.read_csv(Path(directory) / filename)
        columns = ['stage_order', 'stage', 'sessions', 'conversion_from_entry',
                   'conversion_from_previous', 'abandoned_sessions', 'abandonment_rate']
        keys = ['stage_order']
        if scope == 'DEVICE':
            columns = ['device_category', *columns]
            keys = ['device_category', *keys]
        actual = sql.loc[sql.scope.eq(scope), columns]
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
            expected[columns].sort_values(keys).reset_index(drop=True),
            check_dtype=False, rtol=1e-10, atol=1e-12)


def validate(raw_directory, analysis_directory):
    raw_directory, analysis_directory = Path(raw_directory), Path(analysis_directory)
    extraction = json.loads((raw_directory / 'extraction.json').read_text(encoding='utf-8'))
    summary = json.loads((analysis_directory / 'summary.json').read_text(encoding='utf-8'))
    actual_hash = hashlib.sha256((raw_directory / 'events.csv').read_bytes()).hexdigest()
    if extraction['input_sha256'] != actual_hash or summary['input_sha256'] != actual_hash:
        raise ValueError('Input hash mismatch')
    if extraction['audit']['event_rows'] != summary['kpis']['event_count']:
        raise ValueError('Event row-count mismatch')
    compare_funnel(pd.read_csv(raw_directory / 'sql_funnel.csv'), analysis_directory)
    sql_kpis = pd.read_csv(raw_directory / 'sql_user_kpis.csv').iloc[0].to_dict()
    if sql_kpis != {key: summary['kpis'][key] for key in sql_kpis}:
        raise ValueError('Unique-user KPI mismatch')
    return {'validation': 'passed', 'source_table': extraction['source_table'],
            'input_sha256': actual_hash,
            'checks': ['input hashes', 'row reconciliation', 'overall/device ordered funnel', 'unique-user KPIs']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', required=True)
    parser.add_argument('--analysis-dir', required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.raw_dir, args.analysis_dir), indent=2))


if __name__ == '__main__':
    main()
