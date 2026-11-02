"""Package verified GA4 results for Power BI locally; never submits cloud queries."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .cleaning import clean_events
from .foundation import STEPS, summarize
from .multiday import KEYS
from .validate_run import compare_funnel

DATASET_ID = 'ga4_20210101_07_real'
LABELS = ['Product view', 'Add to cart', 'Begin checkout', 'Purchase']
SOURCE_FILES = ['daily_kpis.csv', 'daily_summary.csv', 'daily_funnel.csv',
                'ordered_funnel.csv', 'device_funnel.csv', 'sessions.csv',
                'events.csv', 'extracted_dates.csv', 'summary.json']
PRIMARY_KEYS = {
    'dim_date': ['date'], 'dim_device': ['device_category'], 'dim_stage': ['stage_order'],
    'daily_kpis': ['activity_date'], 'overall_ordered_funnel': ['stage_order'],
    'device_funnel_performance': ['device_category', 'stage_order'],
    'daily_conversion_trends': ['entry_date', 'stage_order'],
    'acquisition_completeness': ['activity_date', 'attribution_field'],
    'quality_indicators': ['indicator'], 'data_coverage': ['date'],
    'window_kpis': ['dataset_id'], 'cohort_sessions': ['session_key'],
    'user_activity': ['activity_date', 'user_key'],
    'session_activity': ['activity_date', 'session_key'],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def equal(actual, expected, keys):
    pd.testing.assert_frame_equal(actual.convert_dtypes().sort_values(keys).reset_index(drop=True),
        expected.convert_dtypes().sort_values(keys).reset_index(drop=True),check_dtype=False,rtol=1e-10,atol=1e-12)


def funnel_export(frame):
    """Rename verified metrics and expose their existing denominators explicitly."""
    groups = [c for c in ['entry_date','device_category'] if c in frame]
    result = frame.sort_values([*groups,'stage_order']).copy()
    group = result.groupby(groups,dropna=False) if groups else None
    result['product_view_denominator'] = (group.sessions.transform('first') if groups
                                          else result.sessions.iloc[0])
    result['previous_stage_denominator'] = group.sessions.shift() if groups else result.sessions.shift()
    result['stage_label'] = result.stage.map(dict(zip(STEPS,LABELS)))
    result = result.rename(columns={'sessions':'ordered_sessions','unique_users':'ordered_unique_users',
        'conversion_from_entry':'conversion_from_product_view_rate',
        'conversion_from_previous':'step_conversion_rate','abandonment_rate':'step_abandonment_rate'})
    for c in ['ordered_sessions','ordered_unique_users','product_view_denominator',
              'previous_stage_denominator','abandoned_sessions','stage_order']:
        result[c] = result[c].astype('Int64')
    return result.reset_index(drop=True)


def build_tables(source, summary):
    """Pure local transformation; no change to source session flags or rate definitions."""
    events,_ = clean_events(source['events'])
    cohort = source['sessions'].copy()
    # Stable within this package, with no reverse mapping or raw identifiers exported.
    users = sorted(set(events.user_pseudo_id.dropna()) | set(cohort.user_pseudo_id.dropna()))
    user_map = {value:i+1 for i,value in enumerate(users)}
    event_pairs = set(events.loc[events.eligible_session,KEYS].itertuples(index=False,name=None))
    cohort_pairs = set(cohort[KEYS].itertuples(index=False,name=None))
    session_map = {value:i+1 for i,value in enumerate(sorted(event_pairs | cohort_pairs))}
    events['user_key'] = events.user_pseudo_id.map(user_map).astype('Int64')
    events['session_key'] = pd.Series([session_map.get(pair) for pair in events[KEYS].itertuples(index=False,name=None)],dtype='Int64')
    cohort['user_key'] = cohort.user_pseudo_id.map(user_map).astype('Int64')
    cohort['session_key'] = [session_map[pair] for pair in cohort[KEYS].itertuples(index=False,name=None)]
    cohort = cohort.drop(columns=KEYS)
    daily = source['daily_kpis'].rename(columns={'event_date':'activity_date','events':'event_count',
        'active_users':'daily_active_users','active_sessions':'daily_active_sessions',
        'entry_sessions':'entry_cohort_sessions'}).copy()
    attribution = []
    for field in ['source','medium']:
        t=daily[['activity_date','event_count',f'missing_{field}_events',f'missing_{field}_rate']].copy()
        t=t.rename(columns={f'missing_{field}_events':'missing_events',f'missing_{field}_rate':'missing_rate',
                            'event_count':'event_denominator'})
        t['attribution_field']=field
        t['available_events']=t.event_denominator-t.missing_events
        t['completeness_rate']=t.available_events/t.event_denominator.replace(0,float('nan'))
        attribution.append(t)
    q=summary['quality']
    quality=[]
    definitions = {
        'window_projected_duplicates':('warning','Repeated projected window event rows, retained by policy'),
        'window_missing_user_rows':('warning','Window event rows missing normalized pseudonym'),
        'window_missing_session_rows':('warning','Window event rows missing session ID'),
        'window_unknown_device_rows':('warning','Window event rows with Unknown normalized device'),
        'cohort_potentially_incomplete':('caution','Cohort sessions touching outer context dates; included'),
        'cross_date_cohort_sessions':('information','Cohort sessions observed on multiple exported dates'),
        'prior_entry_sessions_active_in_window':('information','Window-active sessions entered before analysis window'),
    }
    for name,(severity,definition) in definitions.items():
        denominator=q['cohort_sessions'] if 'cohort' in name else q['window_event_count']
        if name=='prior_entry_sessions_active_in_window':
            denominator=q['window_active_sessions']
        quality.append({'indicator':name,'value':q[name],'denominator':denominator,
            'status':('pass' if q[name]==0 else severity),'definition':definition,'scope':'fixed seven-day window'})
    for check in summary['checks']:
        quality.append({'indicator':'validated: '+check,'value':1,'denominator':1,
                        'status':'pass','definition':check,'scope':'recorded source validation'})
    window = pd.DataFrame([{'dataset_id':DATASET_ID,'source_kind':'REAL_GA4_PUBLIC_SAMPLE',
        'analysis_start':summary['analysis_start'],'analysis_end':summary['analysis_end'],
        'event_count':q['window_event_count'],'unique_users':q['window_unique_users'],
        'window_active_sessions':q['window_active_sessions'],'entry_cohort_sessions':q['cohort_sessions'],
        'product_view_sessions':int(source['ordered_funnel'].sessions.iloc[0]),
        'ordered_purchase_sessions':int(source['ordered_funnel'].sessions.iloc[-1]),
        'product_view_to_purchase_rate':float(source['ordered_funnel'].conversion_from_entry.iloc[-1]),
        'potentially_incomplete_cohort_sessions':q['cohort_potentially_incomplete']}])
    coverage=source['extracted_dates'].rename(columns={'event_date':'date','events':'extracted_events'}).copy()
    coverage['is_analysis_date']=coverage.date.between(pd.Timestamp(summary['analysis_start']),pd.Timestamp(summary['analysis_end']))
    return {
        'dim_date':pd.DataFrame({'date':pd.date_range(summary['analysis_start'],summary['analysis_end'])}),
        'dim_device':pd.DataFrame({'device_category':sorted(cohort.device_category.unique())}),
        'dim_stage':pd.DataFrame({'stage_order':range(1,5),'stage':STEPS,'stage_label':LABELS}),
        'daily_kpis':daily,
        'overall_ordered_funnel':funnel_export(source['ordered_funnel']),
        'device_funnel_performance':funnel_export(source['device_funnel']),
        'daily_conversion_trends':funnel_export(source['daily_funnel']),
        'acquisition_completeness':pd.concat(attribution,ignore_index=True),
        'quality_indicators':pd.DataFrame(quality),'data_coverage':coverage,'window_kpis':window,
        'cohort_sessions':cohort,
        'user_activity':events.loc[events.user_key.notna(),['event_date','user_key']].drop_duplicates().rename(columns={'event_date':'activity_date'}),
        'session_activity':events.loc[events.eligible_session,['event_date','session_key']].drop_duplicates().rename(columns={'event_date':'activity_date'}),
    }


def validate_tables(tables, source, summary):
    for name,keys in PRIMARY_KEYS.items():
        if tables[name][keys].isna().any().any() or tables[name].duplicated(keys).any():
            raise ValueError(f'Invalid primary key: {name}')
    q=summary['quality']
    cohort=tables['cohort_sessions'].assign(user_pseudo_id=tables['cohort_sessions'].user_key)
    carried=[c for c in source['sessions'] if c not in KEYS]
    equal(tables['cohort_sessions'][carried],source['sessions'][carried],carried)
    if len(cohort)!=q['cohort_sessions'] or tables['daily_kpis'].event_count.sum()!=q['window_event_count']:
        raise ValueError('Source total mismatch')
    if tables['user_activity'].user_key.nunique()!=q['window_unique_users']:
        raise ValueError('Distinct user mismatch')
    if tables['session_activity'].session_key.nunique()!=q['window_active_sessions']:
        raise ValueError('Distinct active session mismatch')
    # Verify every derived funnel field against its explicit integer denominators.
    for name in ['overall_ordered_funnel','device_funnel_performance','daily_conversion_trends']:
        t=tables[name]
        for rate,denom in [('conversion_from_product_view_rate','product_view_denominator'),
                           ('step_conversion_rate','previous_stage_denominator')]:
            pd.testing.assert_series_equal(t[rate].astype('Float64'),
                (t.ordered_sessions/t[denom].replace(0,pd.NA)).astype('Float64'),
                check_names=False,rtol=1e-10,atol=1e-12)
        pd.testing.assert_series_equal(t.abandoned_sessions,
            t.previous_stage_denominator-t.ordered_sessions,check_names=False)
        pd.testing.assert_series_equal(t.step_abandonment_rate.astype('Float64'),
            (1-t.step_conversion_rate).astype('Float64'),check_names=False,rtol=1e-10,atol=1e-12)
    # Filter-aware facts must reproduce all source aggregate slices, not just grand totals.
    equal(summarize(cohort),source['ordered_funnel'],['stage_order'])
    for device,group in cohort.groupby('device_category'):
        equal(summarize(group),source['device_funnel'].loc[source['device_funnel'].device_category.eq(device)].drop(columns='device_category'),['stage_order'])
    for day,group in cohort.groupby('entry_date'):
        equal(summarize(group),source['daily_funnel'].loc[source['daily_funnel'].entry_date.eq(day)].drop(columns='entry_date'),['stage_order'])
    for table,key in [('user_activity','user_key'),('session_activity','session_key')]:
        actual=tables[table].groupby('activity_date')[key].nunique()
        col='daily_active_users' if key=='user_key' else 'daily_active_sessions'
        expected=tables['daily_kpis'].set_index('activity_date')[col]
        pd.testing.assert_series_equal(actual,expected,check_names=False,check_dtype=False)
    clean,_=clean_events(source['events'])
    daily=clean.groupby('event_date').agg(event_count=('event_name','size'))
    for field in ['source','medium']:
        daily[f'missing_{field}_events']=clean[field].eq('Unknown').groupby(clean.event_date).sum()
        daily[f'missing_{field}_rate']=daily[f'missing_{field}_events']/daily.event_count
        a=tables['acquisition_completeness'].query('attribution_field == @field').set_index('activity_date')
        pd.testing.assert_series_equal(a.missing_events,daily[f'missing_{field}_events'],check_names=False,check_dtype=False)
        pd.testing.assert_series_equal(a.event_denominator,daily.event_count,check_names=False,check_dtype=False)
        pd.testing.assert_series_equal(a.missing_rate,daily[f'missing_{field}_rate'],check_names=False,check_dtype=False)
        pd.testing.assert_series_equal(a.completeness_rate,1-a.missing_rate,check_names=False,check_dtype=False)
    equal(tables['daily_kpis'][['activity_date',*daily.columns]],daily.reset_index().rename(columns={'event_date':'activity_date'}),['activity_date'])
    # Only dimension-to-fact joins are allowed. Validate uniqueness, coverage and fanout.
    joins=[('dim_date','date','daily_kpis','activity_date'),
           ('dim_date','date','cohort_sessions','entry_date'),
           ('dim_date','date','user_activity','activity_date'),
           ('dim_date','date','session_activity','activity_date'),
           ('dim_date','date','acquisition_completeness','activity_date'),
           ('dim_device','device_category','cohort_sessions','device_category')]
    for dim,dk,fact,fk in joins:
        joined=tables[fact].merge(tables[dim],left_on=fk,right_on=dk,validate='many_to_one',how='left',indicator=True)
        if len(joined)!=len(tables[fact]) or not joined._merge.eq('both').all():
            raise ValueError(f'Invalid relationship {dim} to {fact}')
    return ['primary keys unique and non-null','all source KPI and cohort/device/daily counts agree',
            'rate/abandonment numerator-denominator checks','date-filterable distinct users and sessions agree',
            'dimension joins preserve row counts with no orphan keys']


def load_source(directory):
    result={}
    for filename in SOURCE_FILES:
        if not filename.endswith('.csv'):
            continue
        name=filename[:-4]
        frame=pd.read_csv(directory/filename,dtype={'user_pseudo_id':'string','ga_session_id':'Int64'})
        if name=='events':
            frame=pd.read_csv(directory/filename,dtype='string')
        for c in ['entry_date','event_date','first_date','last_date']:
            if c in frame and name!='events':
                frame[c]=pd.to_datetime(frame[c])
        result[name]=frame
    return result


def export(source_dir,raw_dir,output):
    source_dir,raw_dir,output=Path(source_dir),Path(raw_dir),Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new/empty; verified results are never overwritten')
    summary=json.loads((source_dir/'summary.json').read_text())
    provenance=json.loads((raw_dir/'extraction.json').read_text())
    if (summary.get('validation')!='passed' or not summary.get('checks')
        or not provenance.get('source_table','').startswith('bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_')
        or summary.get('analysis_start')!='2021-01-01' or summary.get('analysis_end')!='2021-01-07'
        or summary['input_sha256']!=provenance['input_sha256']
        or sha(raw_dir/'events.csv')!=provenance['input_sha256']):
        raise ValueError('Verified real GA4 provenance required; fixture export is not allowed')
    before={f:sha(source_dir/f) for f in SOURCE_FILES}
    source=load_source(source_dir)
    # Verify the window export actually matches the authenticated raw-context source.
    raw=pd.read_csv(raw_dir/'events.csv',dtype='string')
    bounded=raw.loc[raw.event_date.between('20210101','20210107')]
    equal(source['events'],bounded,list(raw.columns))
    if len(raw)!=provenance['audit']['event_rows']:
        raise ValueError('Raw extraction row count mismatch')
    tables=build_tables(source,summary)
    checks=validate_tables(tables,source,summary)
    # Compare existing independent SQL audit, without any new cloud jobs.
    compare_funnel(pd.read_csv(source_dir/'duckdb_funnel.csv'),source_dir)
    output.mkdir(parents=True,exist_ok=True)
    files={}
    for name,frame in tables.items():
        for c in frame:
            if pd.api.types.is_datetime64_any_dtype(frame[c]):
                frame[c]=frame[c].dt.strftime('%Y-%m-%d')
        path=output/f'{name}.csv'
        frame.to_csv(path,index=False,encoding='utf-8-sig')
        read=pd.read_csv(path)
        equal(read,frame.astype({c:str for c in frame if frame[c].dtype=='object'}),PRIMARY_KEYS[name])
        files[path.name]={'rows':len(frame),'sha256':sha(path),'primary_key':PRIMARY_KEYS[name],
                          'columns':list(frame.columns)}
    if before!={f:sha(source_dir/f) for f in SOURCE_FILES}:
        raise ValueError('Source changed during packaging')
    manifest={'dataset_id':DATASET_ID,'source_kind':'REAL_GA4_PUBLIC_SAMPLE',
        'validation':'passed','source_input_sha256':summary['input_sha256'],
        'source_files':before,'files':files,'checks':checks+['export CSV round-trip matches source values',
            'raw window rows match extraction','existing DuckDB reference funnel agrees','source files unchanged'],
        'power_bi_desktop_verified':False,'pbix_created':False}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/processed/ga4/20210101_07_verified'))
    parser.add_argument('--raw-dir',type=Path,default=Path('data/raw/ga4/20210101_07_context'))
    parser.add_argument('--output',type=Path,default=Path('powerbi/data/ga4_20210101_07'))
    args=parser.parse_args()
    result=export(args.source,args.raw_dir,args.output)
    print(json.dumps({'dataset_id':result['dataset_id'],'validation':result['validation'],
                      'files':list(result['files']),'pbix_created':False},indent=2))


if __name__=='__main__':
    main()
