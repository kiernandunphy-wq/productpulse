from pathlib import Path
import pandas as pd
import pytest
from productpulse.cleaning import clean_events
from productpulse.analytics import session_table, funnel_table, retention_table
from productpulse.experiment import simulate, analyze
from productpulse.pipeline import run

FIXTURE = Path(__file__).resolve().parents[1] / 'data/fixtures/events.csv'


def loaded():
    return clean_events(pd.read_csv(FIXTURE, dtype='string'))


def test_missing_schema_rejected():
    with pytest.raises(ValueError, match='Missing required'):
        clean_events(pd.DataFrame({'event_name': ['purchase']}))


def test_cleaning_reports_missing_and_preserves_users():
    events, quality = loaded()
    assert quality['excluded_session_rows'] == 2
    assert events.source.eq('Unknown').sum() == 2
    assert events.user_pseudo_id.isna().sum() == 1


def test_ordered_funnel_and_session_key():
    events, _ = loaded()
    sessions = session_table(events)
    assert len(sessions) == 4  # u1 and u2 share session ID but remain separate
    funnel = funnel_table(sessions)
    assert funnel.sessions.tolist() == [4, 4, 2, 2]
    assert funnel.rate_from_entry.iloc[-1] == .5
    assert sessions.any_purchase.sum() == 3  # out-of-order cart excluded from strict funnel


def test_ties_do_not_advance_and_later_valid_cart_is_used():
    events, _ = loaded()
    sample = events[events.user_pseudo_id.eq('u1') & events.ga_session_id.eq(1)].copy()
    sample.loc[sample.event_name.eq('view_item'), 'event_timestamp'] = sample.event_timestamp.min()
    assert session_table(sample).purchase.sum() == 0
    events.loc[events.user_pseudo_id.eq('u3') & events.event_name.eq('add_to_cart'), 'event_timestamp'] = 1604188802500000
    assert session_table(events).purchase.sum() == 3


def test_retention_and_zero_cells():
    events, _ = loaded()
    retention = retention_table(events)
    november = retention[retention.cohort_month.eq('2020-11')]
    assert november.active_users.tolist() == [3, 1]
    assert november.retention_rate.iloc[1] == pytest.approx(1/3)


def test_invalid_date_and_fractional_identifier():
    raw = pd.read_csv(FIXTURE, dtype='string')
    raw.loc[0, 'event_date'] = 'invalid'
    with pytest.raises(ValueError, match='Invalid event'):
        clean_events(raw)
    raw.loc[0, 'event_date'] = '20201101'
    raw.loc[0, 'ga_session_id'] = '1.5'
    with pytest.raises(ValueError, match='integers'):
        clean_events(raw)


def test_empty_denominators():
    events, _ = loaded()
    empty = events.iloc[:0]
    assert funnel_table(session_table(empty)).sessions.sum() == 0
    assert funnel_table(session_table(empty)).rate_from_entry.isna().all()


def test_experiment_reproducibility_and_effect_direction():
    a, b = simulate(), simulate()
    pd.testing.assert_frame_equal(a, b)
    result = analyze(a)
    assert result['ci95_newcombe'][0] < result['absolute_difference'] < result['ci95_newcombe'][1]
    assert 0 <= result['p_two_sided'] <= 1
    assert result['planned_n_per_arm_8_to_9_5_percent'] > 1000


def test_pipeline_outputs(tmp_path):
    manifest = run(FIXTURE, tmp_path, 'fixture')
    assert manifest['eligible_sessions'] == 4
    assert pd.read_csv(tmp_path / 'funnel.csv').sessions.tolist() == [4,4,2,2]
    assert (tmp_path / 'funnel.png').exists()


def test_missing_mature_retention_cell_is_zero_and_future_absent():
    events, _ = loaded()
    events.loc[events.user_pseudo_id.eq('u1') & events.ga_session_id.eq(3), 'user_pseudo_id'] = 'u5'
    table = retention_table(events)
    assert table.loc[(table.cohort_month == '2020-11') & (table.month_index == 1), 'active_users'].item() == 0
    assert len(table[table.cohort_month == '2020-12']) == 1


def test_projected_duplicates_reported_but_retained():
    raw = pd.read_csv(FIXTURE, dtype='string')
    events, quality = clean_events(pd.concat([raw, raw.iloc[:1]], ignore_index=True))
    assert quality['exact_duplicate_rows'] == 1
    assert len(events) == 17
    assert funnel_table(session_table(events)).sessions.tolist() == [4,4,2,2]
