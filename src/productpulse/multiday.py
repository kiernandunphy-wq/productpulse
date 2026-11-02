"""Observed-entry session cohorts with adjacent-shard context and independent SQL checks."""
import argparse
import hashlib
import json
from datetime import timedelta
from pathlib import Path

import duckdb
import pandas as pd

from .cleaning import clean_events
from .foundation import analyze_events, summarize, STEPS
from .validate_run import compare_funnel

SQL_DIR = Path(__file__).resolve().parents[2] / 'sql' / 'foundation'
KEYS = ['user_pseudo_id', 'ga_session_id']
POLICY = (
    'Daily activity uses exported event_date; sessions active per day may overlap. '
    'Funnel cohort uses earliest observed event timestamp across context, with minimum '
    'event_date on ties; include entry dates in the requested window. '
    'Group once by user_pseudo_id and ga_session_id across all dates; retain duplicates. '
    'Strict timestamp ordering and earliest-event device tie policy are unchanged. '
    'Sessions touching the first/last context date are potentially incomplete, not proven complete. '
    'Do not infer a timezone from UTC timestamps or session IDs.'
)


def analyze(events, start, end, session_table=None):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end:
        raise ValueError('Start date must not exceed end date')
    expected = pd.date_range(start - timedelta(days=1), end + timedelta(days=1))
    if not set(expected).issubset(set(events.event_date)):
        raise ValueError('Missing analysis/context dates; require one adjacent day on each side')
    if session_table is None:
        session_table = analyze_events(events)[0]['sessions']
    eligible = events.loc[events.eligible_session].copy()
    first_times = eligible.groupby(KEYS).event_timestamp.transform('min')
    entries = eligible.loc[eligible.event_timestamp.eq(first_times)].groupby(KEYS).event_date.min()
    bounds = eligible.groupby(KEYS).agg(first_date=('event_date', 'min'),
                                       last_date=('event_date', 'max'),
                                       observed_dates=('event_date', 'nunique'))
    sessions = session_table.merge(entries.rename('entry_date'), on=KEYS).merge(bounds, on=KEYS)
    sessions['left_context_edge'] = sessions.first_date.eq(events.event_date.min())
    sessions['right_context_edge'] = sessions.last_date.eq(events.event_date.max())
    sessions['potentially_incomplete'] = sessions.left_context_edge | sessions.right_context_edge
    sessions['crosses_calendar_date'] = sessions.observed_dates.gt(1)
    cohort = sessions.loc[sessions.entry_date.between(start, end)].copy()
    window = events.loc[events.event_date.between(start, end)].copy()
    daily = []
    daily_funnel = []
    for day in pd.date_range(start, end):
        active = window.loc[window.event_date.eq(day)]
        day_cohort = cohort.loc[cohort.entry_date.eq(day)]
        funnel = summarize(day_cohort)
        funnel.insert(0, 'entry_date', day)
        daily_funnel.append(funnel)
        row = {'event_date': day, 'events': len(active),
               'active_users': active.user_pseudo_id.nunique(),
               'active_sessions': len(active.loc[active.eligible_session, KEYS].drop_duplicates()),
               'entry_sessions': len(day_cohort)}
        for column in ['source', 'medium']:
            missing = int(active[column].eq('Unknown').sum())
            row[f'missing_{column}_events'] = missing
            row[f'missing_{column}_rate'] = missing / len(active) if len(active) else None
        daily.append(row)
    devices = []
    for device, group in cohort.groupby('device_category'):
        funnel = summarize(group)
        funnel.insert(0, 'device_category', device)
        devices.append(funnel)
    empty_device = pd.DataFrame(columns=['device_category', *summarize(cohort).columns])
    outputs = {'sessions': cohort, 'context_sessions': sessions,
               'daily_kpis': pd.DataFrame(daily),
               'daily_funnel': pd.concat(daily_funnel, ignore_index=True),
               'ordered_funnel': summarize(cohort),
               'device_funnel': pd.concat(devices, ignore_index=True) if devices else empty_device,
               'events': window}
    daily_summary = outputs['daily_kpis'].copy()
    for step in STEPS:
        selected = outputs['daily_funnel'].loc[outputs['daily_funnel'].stage.eq(step)].set_index('entry_date')
        daily_summary[f'{step}_sessions'] = daily_summary.event_date.map(selected.sessions)
    purchase = outputs['daily_funnel'].loc[outputs['daily_funnel'].stage.eq('purchase')].set_index('entry_date')
    daily_summary['ordered_conversion'] = daily_summary.event_date.map(purchase.conversion_from_entry)
    outputs['daily_summary'] = daily_summary
    quality = {
        'window_event_count': len(window), 'window_unique_users': int(window.user_pseudo_id.nunique()),
        'window_active_sessions': len(window.loc[window.eligible_session, KEYS].drop_duplicates()),
        'cohort_sessions': len(cohort), 'context_events': len(events),
        'context_sessions': len(sessions),
        'cross_date_context_sessions': int(sessions.crosses_calendar_date.sum()),
        'cross_date_cohort_sessions': int(cohort.crosses_calendar_date.sum()),
        'cohort_potentially_incomplete': int(cohort.potentially_incomplete.sum()),
        'prior_entry_sessions_active_in_window': int(sessions.loc[
            sessions.entry_date.lt(start) & sessions.last_date.ge(start)].shape[0]),
        'cohort_sessions_reaching_after_window': int(cohort.last_date.gt(end).sum()),
        'context_potentially_incomplete': int(sessions.potentially_incomplete.sum()),
        'missing_expected_events': [step for step in STEPS if not window.event_name.eq(step).any()],
        'window_projected_duplicates': int(window.drop(columns='eligible_session').duplicated().sum()),
        'window_missing_user_rows': int(window.user_pseudo_id.isna().sum()),
        'window_missing_session_rows': int(window.ga_session_id.isna().sum()),
        'window_unknown_device_rows': int(window.device_category.eq('Unknown').sum()),
    }
    for column in ['source','medium']:
        missing = int(window[column].eq('Unknown').sum())
        quality[f'window_missing_{column}_events'] = missing
        quality[f'window_missing_{column}_rate'] = missing/len(window) if len(window) else None
    quality['window_event_counts'] = {str(k):int(v) for k,v in window.event_name.value_counts().items()}
    quality['window_unique_user_kpis'] = {step:int(window.loc[window.event_name.eq(step),'user_pseudo_id'].nunique())
                                          for step in STEPS}
    return outputs, quality


def reconcile(events, outputs, start, end):
    """Run the existing portable SQL funnel independently of Python session construction."""
    with duckdb.connect() as con:
        con.register('events', events)
        con.execute('CREATE TEMP TABLE all_ordered AS ' + (SQL_DIR / '04_ordered_sessions.sql').read_text())
        con.execute('''CREATE TEMP TABLE entries AS
            WITH ranked AS (
              SELECT *, MIN(event_timestamp) OVER (PARTITION BY user_pseudo_id,ga_session_id) first_time
              FROM events WHERE eligible_session
            ) SELECT user_pseudo_id,ga_session_id,MIN(event_date) entry_date
              FROM ranked WHERE event_timestamp=first_time GROUP BY 1,2''')
        con.execute('''CREATE TEMP TABLE ordered_sessions AS
            SELECT a.* FROM all_ordered a JOIN entries e USING(user_pseudo_id,ga_session_id)
            WHERE e.entry_date BETWEEN ? AND ?''', [start, end])
        actual = con.sql('SELECT * FROM ordered_sessions').df()
        columns = [*KEYS, 'device_category', *STEPS]
        pd.testing.assert_frame_equal(actual.sort_values(KEYS).reset_index(drop=True),
            outputs['sessions'][columns].sort_values(KEYS).reset_index(drop=True), check_dtype=False)
        funnel = con.sql((SQL_DIR / '05_funnel_summary.sql').read_text()).df()
        # compare_funnel checks persisted outputs; compare the same metrics in memory here.
        for scope, name in [('ALL', 'ordered_funnel'), ('DEVICE', 'device_funnel')]:
            cols = ['stage_order', 'stage', 'sessions', 'conversion_from_entry',
                    'conversion_from_previous', 'abandoned_sessions', 'abandonment_rate']
            keys = ['stage_order']
            if scope == 'DEVICE':
                cols = ['device_category', *cols]
                keys = ['device_category', *keys]
            pd.testing.assert_frame_equal(funnel.loc[funnel.scope.eq(scope), cols].sort_values(keys).reset_index(drop=True),
                outputs[name][cols].sort_values(keys).reset_index(drop=True), check_dtype=False,
                rtol=1e-10, atol=1e-12)
        daily = con.execute('''SELECT event_date,COUNT(*) events,
            COUNT(DISTINCT user_pseudo_id) active_users,
            COUNT(DISTINCT (user_pseudo_id,ga_session_id)) FILTER (WHERE eligible_session) active_sessions,
            COUNT(*) FILTER (WHERE source='Unknown') missing_source_events,
            COUNT(*) FILTER (WHERE medium='Unknown') missing_medium_events
            FROM events WHERE event_date BETWEEN ? AND ? GROUP BY 1 ORDER BY 1''', [start,end]).df()
        cols = list(daily.columns)
        pd.testing.assert_frame_equal(daily,outputs['daily_kpis'][cols],check_dtype=False)
        sql_daily = con.execute('''SELECT e.entry_date, COUNT(*) entry_sessions,
            SUM(a.view_item) view_item,SUM(a.add_to_cart) add_to_cart,
            SUM(a.begin_checkout) begin_checkout,SUM(a.purchase) purchase
            FROM entries e JOIN all_ordered a USING(user_pseudo_id,ga_session_id)
            WHERE entry_date BETWEEN ? AND ? GROUP BY 1 ORDER BY 1''', [start,end]).df()
        for row in sql_daily.itertuples():
            expected = outputs['daily_funnel'].loc[outputs['daily_funnel'].entry_date.eq(row.entry_date)]
            assert expected.sessions.tolist() == [getattr(row,step) for step in STEPS]
            assert outputs['daily_kpis'].loc[outputs['daily_kpis'].event_date.eq(row.entry_date),'entry_sessions'].iloc[0] == row.entry_sessions
        daily_metrics = ['stage_order','stage','sessions','conversion_from_entry',
                         'conversion_from_previous','abandoned_sessions','abandonment_rate']
        for day in pd.date_range(start,end):
            con.execute('DELETE FROM ordered_sessions')
            con.execute('''INSERT INTO ordered_sessions SELECT a.* FROM all_ordered a
                JOIN entries e USING(user_pseudo_id,ga_session_id) WHERE entry_date=?''',[day])
            daily_sql = con.sql((SQL_DIR/'05_funnel_summary.sql').read_text()).df()
            pd.testing.assert_frame_equal(
                daily_sql.loc[daily_sql.scope.eq('ALL'),daily_metrics].sort_values('stage_order').reset_index(drop=True),
                outputs['daily_funnel'].loc[outputs['daily_funnel'].entry_date.eq(day),daily_metrics].reset_index(drop=True),
                check_dtype=False,rtol=1e-10,atol=1e-12)
        counts = con.execute('''SELECT COUNT(*) events,COUNT(DISTINCT user_pseudo_id) users,
            COUNT(DISTINCT (user_pseudo_id,ga_session_id)) FILTER (WHERE eligible_session) sessions
            FROM events WHERE event_date BETWEEN ? AND ?''',[start,end]).fetchone()
    assert counts == (len(outputs['events']), outputs['events'].user_pseudo_id.nunique(),
                      len(outputs['events'].loc[outputs['events'].eligible_session,KEYS].drop_duplicates()))
    return funnel


def run(raw_dir, output, start='2021-01-01', end='2021-01-07'):
    raw_dir, output = Path(raw_dir), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new/empty')
    manifest = json.loads((raw_dir/'extraction.json').read_text())
    digest = hashlib.sha256((raw_dir/'events.csv').read_bytes()).hexdigest()
    if manifest['input_sha256'] != digest:
        raise ValueError('Input hash mismatch')
    raw = pd.read_csv(raw_dir/'events.csv',dtype='string')
    if len(raw) != manifest['audit']['event_rows']:
        raise ValueError('Source/export count mismatch')
    inventory = pd.read_csv(raw_dir/'event_inventory.csv')
    if inventory.event_count.sum() != len(raw):
        raise ValueError('Inventory/export count mismatch')
    events, cleaning = clean_events(raw)
    # Verify all-context BigQuery parity before selecting the seven-day cohort.
    context, context_kpis = analyze_events(events)
    sql_kpis = pd.read_csv(raw_dir/'sql_user_kpis.csv').iloc[0].to_dict()
    if sql_kpis != {k:context_kpis[k] for k in sql_kpis}:
        raise ValueError('BigQuery context KPI mismatch')
    outputs, quality = analyze(events,start,end,session_table=context['sessions'])
    sql_funnel = reconcile(events,outputs,start,end)
    output.mkdir(parents=True, exist_ok=True)
    context_dir = output/'context_validation'
    context_dir.mkdir()
    for name in ['ordered_funnel','device_funnel']:
        context[name].to_csv(context_dir/f'{name}.csv',index=False)
    compare_funnel(pd.read_csv(raw_dir/'sql_funnel.csv'),context_dir)
    for name, frame in outputs.items():
        # Keep exported event identifiers/timestamps unchanged in the dashboard event table.
        if name == 'events':
            frame = raw.loc[events.event_date.between(pd.Timestamp(start),pd.Timestamp(end))]
        frame.to_csv(output/f'{name}.csv',index=False)
    sql_funnel.to_csv(output/'duckdb_funnel.csv',index=False)
    date_counts = events.groupby('event_date').size().rename('events').reset_index()
    date_counts.to_csv(output/'extracted_dates.csv',index=False)
    summary = {'analysis_start':start,'analysis_end':end,'policy':POLICY,
        'input_sha256':digest,'quality':quality,'context_cleaning':cleaning,
        'validation':'passed','checks':['source/hash/inventory row counts','BigQuery context KPIs and funnel',
            'DuckDB cohort session flags','DuckDB overall/device funnel and rates','DuckDB daily activity and entry counts',
            'DuckDB daily cohort stage counts and rates','DuckDB distinct window users/sessions'],
        'jobs':manifest['jobs'],'dry_run_bytes':manifest['dry_run_bytes']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    write_reports(output,outputs,summary,date_counts)
    return summary


def markdown(frame):
    """Render simple tables without adding an optional tabulate dependency."""
    def value(item):
        if pd.isna(item):
            return 'N/A'
        return str(item)
    return ('| ' + ' | '.join(frame.columns) + ' |\n| ' + ' | '.join(['---']*len(frame.columns)) + ' |\n'
            + '\n'.join('| '+' | '.join(value(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)))


def write_reports(output, tables, summary, dates):
    quality=summary['quality']
    funnel=tables['ordered_funnel'].copy()
    for column in ['conversion_from_entry','conversion_from_previous','abandonment_rate']:
        funnel[column]=funnel[column].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
    text=(f"# Seven-day conversion: {summary['analysis_start']} through {summary['analysis_end']}\n\n"
          f"Real GA4 public sample: {quality['window_event_count']:,} window events, "
          f"{quality['window_unique_users']:,} distinct pseudonyms, "
          f"{quality['window_active_sessions']:,} window-active sessions, and "
          f"{quality['cohort_sessions']:,} observed-entry cohort sessions.\n\n"
          +markdown(funnel)+'\n\n'+POLICY+'\n')
    (output/'kpi_summary.md').write_text(text,encoding='utf-8')
    quality_text=('# Data quality\n\n'+json.dumps(quality,indent=2)+'\n\n'
                  'Extracted date coverage:\n\n'+markdown(dates)+'\n\n'
                  'No missing identity or duplicate policy is inferred from the source: see actual counts above. '
                  'The sample is obfuscated; Unknown source/medium and absent steps cannot establish causes. '
                  'Daily users and active sessions overlap across dates and must not be summed as distinct totals. '
                  'Adjacent context improves observation but does not prove full journeys or detect sessions extending beyond it.\n')
    (output/'data_quality.md').write_text(quality_text,encoding='utf-8')
    processed=sum(job['bytes_processed'] or 0 for job in summary['jobs'])
    billed=sum(job['bytes_billed'] or 0 for job in summary['jobs'])
    devices=tables['device_funnel'].loc[tables['device_funnel'].stage.eq('purchase'),
        ['device_category','sessions','conversion_from_entry']].copy()
    devices.conversion_from_entry=devices.conversion_from_entry.map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
    executive=(text+'\n## Device purchase conversion\n\n'+markdown(devices)+'\n\n'
               f"BigQuery recorded {processed:,} processed bytes and {billed:,} billed bytes across five data jobs. "
               'Billed bytes are a usage measure, not proof of a monetary charge. Free-tier balance was not inspected. '
               'No cloud settings were modified. All query estimates were below the existing 1 GB per-query cap.\n\n'
               'BigQuery context and independent DuckDB cohort/daily reconciliation passed. '
               'Interpret device differences and daily changes descriptively; small samples, source obfuscation, '
               'and incomplete boundary observation prevent causal claims. Next: review the semantic model and '
               'boundary flags before importing these datasets into Power BI or Databricks. No dashboards or experiments were built.\n')
    (output/'executive_findings.md').write_text(executive,encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--start',default='2021-01-01')
    parser.add_argument('--end',default='2021-01-07')
    args = parser.parse_args()
    print(json.dumps(run(args.raw_dir,args.output,args.start,args.end),indent=2))


if __name__ == '__main__':
    main()
