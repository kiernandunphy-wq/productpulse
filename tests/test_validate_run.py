"""Reconciliation tests use simulated local artifacts, not BigQuery results."""
import json
from pathlib import Path
import shutil
import duckdb
import pandas as pd
import pytest
from productpulse.cleaning import clean_events
from productpulse.foundation import run
from productpulse.validate_run import validate

ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_and_detection_of_tampered_counts(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    shutil.copyfile(ROOT / 'data/fixtures/foundation_events.csv', raw / 'events.csv')
    analysis = tmp_path / 'analysis'
    summary = run(raw / 'events.csv', analysis, 'fixture')
    events, _ = clean_events(pd.read_csv(raw / 'events.csv', dtype='string'))
    with duckdb.connect() as connection:
        connection.register('events', events)
        connection.execute('CREATE TEMP TABLE ordered_sessions AS ' + (ROOT / 'sql/foundation/04_ordered_sessions.sql').read_text())
        connection.sql((ROOT / 'sql/foundation/05_funnel_summary.sql').read_text()).df().to_csv(raw / 'sql_funnel.csv', index=False)
        connection.sql((ROOT / 'sql/foundation/07_user_kpis.sql').read_text()).df().to_csv(raw / 'sql_user_kpis.csv', index=False)
    (raw / 'extraction.json').write_text(json.dumps({'source_table': 'SYNTHETIC TEST ONLY',
        'input_sha256': summary['input_sha256'], 'audit': {'event_rows': 21}}))
    assert validate(raw, analysis)['validation'] == 'passed'
    broken = pd.read_csv(raw / 'sql_funnel.csv')
    broken.loc[0, 'sessions'] = 999
    broken.to_csv(raw / 'sql_funnel.csv', index=False)
    with pytest.raises(AssertionError):
        validate(raw, analysis)
    (raw / 'events.csv').write_text('tampered')
    with pytest.raises(ValueError, match='hash mismatch'):
        validate(raw, analysis)
