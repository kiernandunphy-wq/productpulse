from pathlib import Path
import json
import duckdb
import pandas as pd
import pytest
from productpulse.cleaning import clean_events
from productpulse.foundation import analyze_events, ordered_sessions, run
from productpulse.bigquery_extract import table_for, sql_bundle, validate_schema

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'data/fixtures/foundation_events.csv'
SQL = ROOT / 'sql/foundation'


def load():
    return clean_events(pd.read_csv(FIXTURE, dtype='string'))[0]


def test_hand_calculated_users_sessions_and_abandonment():
    tables, kpis = analyze_events(load())
    assert kpis == {'unique_users': 4, 'event_count': 21, 'eligible_sessions': 5,
                   'product_viewers': 4, 'add_to_cart_users': 3, 'checkout_starters': 4,
                   'purchasers': 4, 'ordered_session_conversion': .5}
    funnel = tables['ordered_funnel']
    assert funnel.sessions.tolist() == [4,4,2,2]
    assert funnel.unique_users.tolist() == [3,3,1,1]
    assert funnel.abandoned_sessions.iloc[1:].tolist() == [0,2,0]
    assert funnel.abandonment_rate.iloc[1:].tolist() == [0,.5,0]
    assert tables['device_funnel'].query("device_category == 'mobile'").sessions.tolist() == [2,2,1,1]


def test_duplicates_ties_and_valid_later_checkout():
    events = load()
    base = analyze_events(events)[0]['ordered_funnel'].sessions.tolist()
    assert analyze_events(events.drop_duplicates())[0]['ordered_funnel'].sessions.tolist() == base
    # b's checkout equals cart time: still not ordered.
    events.loc[events.user_pseudo_id.eq('b') & events.event_name.eq('begin_checkout'), 'event_timestamp'] = 1609459212000000
    assert analyze_events(events)[0]['ordered_funnel'].sessions.tolist() == base
    events.loc[events.user_pseudo_id.eq('b') & events.event_name.eq('begin_checkout'), 'event_timestamp'] = 1609459212500000
    assert analyze_events(events)[0]['ordered_funnel'].sessions.tolist() == [4,4,3,3]


def test_no_cross_session_conversions_and_missing_values():
    events = load()
    sessions = ordered_sessions(events)
    assert sessions.loc[sessions.user_pseudo_id.eq('c'), 'purchase'].sum() == 0
    assert sessions.user_pseudo_id.notna().all()
    assert sessions.ga_session_id.notna().all()
    events['device_category'] = 'Unknown'
    assert ordered_sessions(events).device_category.eq('Unknown').all()


def test_zero_denominator_and_missing_checkout(tmp_path):
    events = load()
    tables, kpis = analyze_events(events.iloc[:0])
    assert kpis['ordered_session_conversion'] is None
    assert tables['ordered_funnel'].conversion_from_entry.isna().all()
    assert tables['device_funnel'].empty
    raw = pd.read_csv(FIXTURE, dtype='string')
    path = tmp_path / 'no_checkout.csv'
    raw.loc[raw.event_name.ne('begin_checkout')].to_csv(path, index=False)
    summary = run(path, tmp_path / 'output', 'fixture')
    assert summary['missing_expected_events'] == ['begin_checkout']
    assert summary['kpis']['ordered_session_conversion'] == 0


@pytest.mark.parametrize('empty', [False, True])
def test_independent_sql_parity(empty):
    events = load()
    if empty:
        events = events.iloc[:0]
    expected, kpis = analyze_events(events)
    with duckdb.connect() as connection:
        connection.register('events', events)
        core = (SQL / '04_ordered_sessions.sql').read_text(encoding='utf-8')
        connection.execute('CREATE TEMP TABLE ordered_sessions AS ' + core)
        actual = connection.sql('SELECT * FROM ordered_sessions').df()
        keys = ['user_pseudo_id', 'ga_session_id']
        pd.testing.assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
            expected['sessions'].sort_values(keys).reset_index(drop=True), check_dtype=False)
        summary = connection.sql((SQL / '05_funnel_summary.sql').read_text()).df()
        for scope, python in [('ALL', expected['ordered_funnel']), ('DEVICE', expected['device_funnel'])]:
            cols = ['stage_order','stage','sessions','conversion_from_entry','conversion_from_previous',
                    'abandoned_sessions','abandonment_rate']
            keys = ['stage_order']
            if scope == 'DEVICE':
                cols = ['device_category', *cols]
                keys = ['device_category', *keys]
            pd.testing.assert_frame_equal(summary.loc[summary.scope.eq(scope), cols].sort_values(keys).reset_index(drop=True),
                python[cols].sort_values(keys).reset_index(drop=True), check_dtype=False)
        reach = connection.sql((SQL / '06_user_reach.sql').read_text()).df()
        pd.testing.assert_frame_equal(reach.sort_values('event_name').reset_index(drop=True),
            expected['event_reach'].sort_values('event_name').reset_index(drop=True), check_dtype=False)
        user_kpis = connection.sql((SQL / '07_user_kpis.sql').read_text()).df().iloc[0].to_dict()
        assert user_kpis == {key: kpis[key] for key in user_kpis}


def test_provenance_and_protect_existing_output(tmp_path):
    directory = tmp_path / 'run'
    summary = run(FIXTURE, directory, 'fixture')
    saved = json.loads((directory / 'summary.json').read_text())
    assert saved == summary
    assert summary['quality']['exact_duplicate_rows'] == 1
    with pytest.raises(ValueError, match='empty'):
        run(FIXTURE, directory, 'fixture')


def test_date_validation_and_single_shard_bundle():
    table = table_for('2021-01-01')
    bundle = sql_bundle(table)
    assert 'begin_checkout' in bundle['ordered_sessions']
    assert 'events_*' not in ''.join(bundle.values())
    with pytest.raises(ValueError):
        table_for('2022-01-01')
    with pytest.raises(ValueError):
        table_for('2021-01-01` injection')


def test_schema_mismatch_is_not_silently_accepted():
    with pytest.raises(ValueError, match='Schema contract mismatch'):
        validate_schema([])


def test_invalid_session_is_not_silently_dropped():
    raw = pd.read_csv(FIXTURE, dtype='string')
    raw.loc[0, 'ga_session_id'] = 'broken'
    with pytest.raises(ValueError, match='nonnumeric'):
        clean_events(raw)
