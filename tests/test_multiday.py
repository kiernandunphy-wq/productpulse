import pandas as pd
import pytest
import sqlglot

from productpulse.bigquery_extract import range_bundle
from productpulse.cleaning import clean_events
from productpulse.multiday import analyze, reconcile


def sample():
    rows = []
    def add(day, user, session, event, offset=0, device='mobile'):
        timestamp = pd.Timestamp(day).value // 1000 + offset
        rows.append([pd.Timestamp(day).strftime('%Y%m%d'), timestamp, event,
                     user, session, None, '(not set)', device])
    for day in pd.date_range('2020-12-31','2021-01-08'):
        add(day,'daily',100+day.day,'page_view')
    add('2021-01-01','midnight',1,'view_item',86_399_000_000)
    add('2021-01-02','midnight',1,'add_to_cart',1)
    add('2021-01-02','midnight',1,'begin_checkout',2)
    add('2021-01-02','midnight',1,'purchase',3)
    add('2020-12-31','prior',2,'view_item')
    add('2021-01-01','prior',2,'purchase')
    add('2021-01-07','right',3,'view_item')
    add('2021-01-08','right',3,'add_to_cart',1)
    add('2021-01-08','right',3,'begin_checkout',2)
    add('2021-01-08','right',3,'purchase',3)
    add('2021-01-02',None,None,'purchase',4)
    add('2021-01-02','ties',4,'view_item',5,device='tablet')
    add('2021-01-02','ties',4,'add_to_cart',5,device='desktop')
    return clean_events(pd.DataFrame(rows,columns=['event_date','event_timestamp','event_name',
        'user_pseudo_id','ga_session_id','source','medium','device_category']))[0]


def test_midnight_session_counted_once_and_daily_activity_overlaps():
    events=sample()
    tables,q=analyze(events,'2021-01-01','2021-01-07')
    row=tables['sessions'].query("user_pseudo_id == 'midnight'").iloc[0]
    assert row.entry_date == pd.Timestamp('2021-01-01')
    assert row.purchase == 1
    assert row.crosses_calendar_date
    assert not row.potentially_incomplete
    assert q['cross_date_cohort_sessions'] == 2
    daily = tables['daily_funnel']
    assert daily.loc[daily.entry_date.eq(pd.Timestamp('2021-01-01')) & daily.stage.eq('purchase'),'sessions'].iloc[0] == 1
    assert tables['daily_kpis'].active_sessions.sum() > q['window_active_sessions']
    reconcile(events,tables,'2021-01-01','2021-01-07')


def test_boundary_sessions_and_timestamp_ties():
    tables,q=analyze(sample(),'2021-01-01','2021-01-07')
    assert 'prior' not in set(tables['sessions'].user_pseudo_id)
    right=tables['sessions'].query("user_pseudo_id == 'right'").iloc[0]
    assert right.purchase == 1 and right.right_context_edge
    assert q['prior_entry_sessions_active_in_window'] == 1
    assert q['cohort_sessions_reaching_after_window'] == 1
    assert q['cohort_potentially_incomplete'] == 1
    ties=tables['sessions'].query("user_pseudo_id == 'ties'").iloc[0]
    assert ties.add_to_cart == 0
    assert ties.device_category == 'desktop'


def test_duplicate_and_missing_identity_policy():
    events=sample()
    original,q=analyze(events,'2021-01-01','2021-01-07')
    duplicate=pd.concat([events,events.loc[events.user_pseudo_id.eq('midnight')]],ignore_index=True)
    tables,quality=analyze(duplicate,'2021-01-01','2021-01-07')
    assert quality['window_projected_duplicates'] == 4
    assert quality['window_missing_user_rows'] == quality['window_missing_session_rows'] == 1
    assert original['ordered_funnel'].sessions.tolist() == tables['ordered_funnel'].sessions.tolist()
    assert tables['daily_kpis'].missing_source_rate.eq(1).all()
    reconcile(duplicate,tables,'2021-01-01','2021-01-07')


def test_missing_context_and_reversed_range_fail():
    events=sample()
    with pytest.raises(ValueError,match='Missing analysis/context'):
        analyze(events.loc[events.event_date.ne(pd.Timestamp('2021-01-08'))],'2021-01-01','2021-01-07')
    with pytest.raises(ValueError,match='Start date'):
        analyze(events,'2021-01-07','2021-01-01')
    with pytest.raises(ValueError,match='Start date'):
        range_bundle('2021-01-07','2021-01-01')


def test_pruned_range_sql():
    for text in range_bundle('2020-12-31','2021-01-08').values():
        assert "_TABLE_SUFFIX BETWEEN '20201231' AND '20210108'" in text
        assert sqlglot.parse_one(text,read='bigquery') is not None
