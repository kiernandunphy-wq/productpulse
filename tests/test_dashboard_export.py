"""Local packaging checks; no cloud calls or Power BI Desktop integration claims."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from productpulse.dashboard_export import (export, load_source, build_tables,
    validate_tables, funnel_export, PRIMARY_KEYS)
from productpulse.foundation import summarize

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/processed/ga4/20210101_07_verified'
RAW=ROOT/'data/raw/ga4/20210101_07_context'


@pytest.fixture
def verified():
    if not (SOURCE/'summary.json').exists():
        pytest.skip('Local verified GA4 outputs are private and not distributed')
    source=load_source(SOURCE)
    summary=json.loads((SOURCE/'summary.json').read_text())
    return source,summary


def test_zero_denominators_and_stage_total_policy():
    empty=pd.DataFrame(columns=['user_pseudo_id','view_item','add_to_cart','begin_checkout','purchase'])
    t=funnel_export(summarize(empty))
    assert t.ordered_sessions.tolist()==[0,0,0,0]
    assert t.conversion_from_product_view_rate.isna().all()
    assert t.step_conversion_rate.isna().all()
    assert pd.isna(t.previous_stage_denominator.iloc[0])
    assert t.abandoned_sessions.iloc[1:].eq(0).all()


def test_all_real_kpis_and_surrogate_keys(verified):
    source,summary=verified
    tables=build_tables(source,summary)
    assert validate_tables(tables,source,summary)
    assert tables['window_kpis'].event_count.iloc[0]==245209
    assert tables['window_kpis'].unique_users.iloc[0]==22847
    assert tables['overall_ordered_funnel'].ordered_sessions.tolist()==[3942,743,190,91]
    assert tables['cohort_sessions'].potentially_incomplete.sum()==4
    assert not any(c in ['user_pseudo_id','ga_session_id'] for t in tables.values() for c in t)
    assert tables['user_activity'].user_key.nunique()==22847
    assert tables['session_activity'].session_key.nunique()==26331
    assert len(tables['cohort_sessions'])==26328


def test_nonadditive_users_and_multidate_session_counts(verified):
    source,summary=verified
    t=build_tables(source,summary)
    assert t['daily_kpis'].daily_active_users.sum()>t['user_activity'].user_key.nunique()
    assert t['daily_kpis'].daily_active_sessions.sum()>t['session_activity'].session_key.nunique()
    # Simulate date/device filters by selecting fact rows, not summing static aggregates.
    for date in t['dim_date'].date:
        for device in t['dim_device'].device_category:
            rows=t['cohort_sessions'].loc[t['cohort_sessions'].entry_date.eq(date)&t['cohort_sessions'].device_category.eq(device)]
            assert len(rows)==rows.session_key.nunique()
            assert rows.purchase.sum()<=rows.begin_checkout.sum()<=rows.add_to_cart.sum()<=rows.view_item.sum()


@pytest.mark.parametrize('tamper',['duplicate_dim','duplicate_fact','rate','attribution','daily_total'])
def test_invalid_exports_are_rejected(verified,tamper):
    source,summary=verified
    t=build_tables(source,summary)
    if tamper=='duplicate_dim':
        t['dim_device']=pd.concat([t['dim_device'],t['dim_device'].iloc[:1]])
    elif tamper=='duplicate_fact':
        t['cohort_sessions']=pd.concat([t['cohort_sessions'],t['cohort_sessions'].iloc[:1]])
    elif tamper=='rate':
        t['overall_ordered_funnel'].loc[3,'conversion_from_product_view_rate']=.9
    elif tamper=='attribution':
        t['acquisition_completeness'].loc[0,'missing_events']+=1
    else:
        t['daily_kpis'].loc[0,'event_count']+=1
    with pytest.raises((ValueError,AssertionError)):
        validate_tables(t,source,summary)


def test_export_roundtrip_and_source_preservation(verified,tmp_path):
    if not (RAW/'events.csv').exists():
        pytest.skip('Private raw data absent')
    result=export(SOURCE,RAW,tmp_path/'package')
    assert result['validation']=='passed'
    assert result['source_kind']=='REAL_GA4_PUBLIC_SAMPLE'
    assert result['pbix_created'] is False
    assert set(f[:-4] for f in result['files'])==set(PRIMARY_KEYS)
    for file,meta in result['files'].items():
        frame=pd.read_csv(tmp_path/'package'/file)
        assert len(frame)==meta['rows']
        assert not frame.duplicated(meta['primary_key']).any()
    with pytest.raises(ValueError,match='new/empty'):
        export(SOURCE,RAW,tmp_path/'package')


def test_fixture_provenance_rejected(tmp_path):
    source,raw=tmp_path/'source',tmp_path/'raw'
    source.mkdir();raw.mkdir()
    (source/'summary.json').write_text(json.dumps({'label':'fixture','validation':'fixture only'}))
    (raw/'extraction.json').write_text(json.dumps({'source_table':'synthetic'}))
    with pytest.raises(ValueError,match='real GA4 provenance'):
        export(source,raw,tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_filter_model_never_joins_aggregates_to_facts(verified):
    source,summary=verified
    t=build_tables(source,summary)
    before=len(t['cohort_sessions'])
    joined=t['cohort_sessions'].merge(t['dim_date'],left_on='entry_date',right_on='date',validate='many_to_one')
    joined=joined.merge(t['dim_device'],on='device_category',validate='many_to_one')
    assert len(joined)==before
    assert joined.purchase.sum()==91
    bad=copy.deepcopy(t)
    bad['dim_date']=bad['dim_date'].iloc[:-1]
    with pytest.raises(ValueError,match='relationship'):
        validate_tables(bad,source,summary)
