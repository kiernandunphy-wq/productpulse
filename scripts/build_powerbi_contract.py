"""Generate field-level audit, dictionary and explicitly typed import expressions locally."""
import argparse
from pathlib import Path

import pandas as pd

from productpulse.dashboard_export import PRIMARY_KEYS

TEXT = {'dataset_id','source_kind','device_category','stage','stage_label','attribution_field',
        'indicator','status','definition','scope'}
DATES = {'date','activity_date','entry_date','first_date','last_date','analysis_start','analysis_end'}
BOOLS = {'is_analysis_date','left_context_edge','right_context_edge','potentially_incomplete','crosses_calendar_date'}
DESCRIPTIONS = {
    'date':'Dimension or coverage exported calendar date.',
    'activity_date':'Exported calendar date of observed activity; not inferred from UTC timestamp.',
    'entry_date':'Exported date at earliest observed cohort timestamp across context; minimum date on ties.',
    'first_date':'Minimum exported event date observed for this composite session in context.',
    'last_date':'Maximum exported event date observed for this composite session in context.',
    'observed_dates':'Number of distinct exported dates observed for the session in context.',
    'left_context_edge':'Session touches first extracted context date; completeness uncertain.',
    'right_context_edge':'Session touches last extracted context date; completeness uncertain.',
    'potentially_incomplete':'Either context edge flag; retained in primary metrics.',
    'crosses_calendar_date':'More than one exported calendar date observed for one session.',
    'stage_order':'Ordered stage index 1=view, 2=cart, 3=checkout, 4=purchase; never additive.',
    'stage':'Source event name corresponding to the ordered stage.',
    'stage_label':'Human-readable ordered funnel stage; sort by stage_order.',
    'device_category':'Normalized device from earliest session event; lexicographic device on timestamp ties.',
    'event_count':'Calendar-window event rows, with duplicates retained.',
    'daily_active_users':'Distinct non-null pseudonyms observed on that day; nonadditive across dates.',
    'daily_active_sessions':'Distinct eligible composite session keys active on that day; nonadditive across dates.',
    'entry_cohort_sessions':'Sessions with observed entry date in the row/window; additive across entry dates.',
    'missing_source_events':'Calendar events with normalized Unknown first-user acquisition source.',
    'missing_medium_events':'Calendar events with normalized Unknown first-user acquisition medium.',
    'missing_source_rate':'missing_source_events / event_count; event-weighted, not user-weighted.',
    'missing_medium_rate':'missing_medium_events / event_count; event-weighted, not user-weighted.',
    'ordered_sessions':'Eligible cohort sessions reaching this stage in strict timestamp order.',
    'ordered_unique_users':'Distinct pseudonyms reaching the ordered stage; nonadditive across dates/devices/stages.',
    'product_view_denominator':'Product-view sessions in the same date/device scope; repeated across stage rows.',
    'previous_stage_denominator':'Previous ordered-stage sessions in same scope; blank for stage 1.',
    'conversion_from_product_view_rate':'ordered_sessions / product_view_denominator; undefined denominator is blank.',
    'step_conversion_rate':'ordered_sessions / previous_stage_denominator; first-stage/zero denominator is blank.',
    'abandoned_sessions':'previous_stage_denominator minus ordered_sessions; blank for first stage.',
    'step_abandonment_rate':'1 minus step_conversion_rate; undefined rates remain blank.',
    'attribution_field':'source or medium; separate field scopes, not unique missing-event categories.',
    'event_denominator':'Calendar event rows for this date and selected field; repeated for source/medium.',
    'missing_events':'Events whose selected acquisition field is Unknown under existing normalization.',
    'missing_rate':'missing_events / event_denominator; do not average across dates.',
    'available_events':'event_denominator minus missing_events for the selected field.',
    'completeness_rate':'available_events / event_denominator; field-scoped event completeness.',
    'indicator':'Unique quality or recorded validation indicator; fixed-window/context scope.',
    'value':'Count for quality rows; 1 means passed for recorded validation rows. Read definition.',
    'denominator':'Relevant event/session population, or 1 for validation; not additive across indicators.',
    'status':'pass, caution, warning or information; not a live cloud/Power BI status.',
    'definition':'Human-readable indicator definition; use with value and denominator.',
    'scope':'Explicit fixed-window or recorded-source-validation scope.',
    'extracted_events':'Source-export event rows per date including adjacent context shards.',
    'is_analysis_date':'True for Jan 1–7; false for the two context dates.',
    'dataset_id':'Fixed identifier ga4_20210101_07_real; package is not synthetic.',
    'source_kind':'REAL_GA4_PUBLIC_SAMPLE; recorded provenance validated before export.',
    'analysis_start':'Inclusive first requested exported analysis date.',
    'analysis_end':'Inclusive final requested exported analysis date.',
    'unique_users':'Distinct non-null pseudonyms in full calendar window; not sum of daily users.',
    'window_active_sessions':'Distinct eligible composite sessions active at least once in the window.',
    'product_view_sessions':'Full-window observed-entry cohort sessions with ordered view_item flag.',
    'ordered_purchase_sessions':'Full-window cohort sessions completing all four ordered stages.',
    'product_view_to_purchase_rate':'ordered_purchase_sessions / product_view_sessions, not all sessions.',
    'potentially_incomplete_cohort_sessions':'Included cohort sessions touching first/last context dates.',
    'session_key':'Package-local positive integer surrogate for original user+session tuple; not a source ID.',
    'user_key':'Package-local positive integer surrogate for a source pseudonym; no identity mapping exported.',
    'view_item':'Binary established ordered product-view reach flag for this session.',
    'add_to_cart':'Binary established ordered cart reach flag after strictly earlier view.',
    'begin_checkout':'Binary established ordered checkout reach flag after strictly earlier cart.',
    'purchase':'Binary established ordered purchase reach flag after strictly earlier checkout.',
}
MODEL_NAMES = {
    'dim_date':'DimDate','dim_device':'DimDevice','dim_stage':'DimStage','daily_kpis':'DailyKpis',
    'overall_ordered_funnel':'AuditOverallFunnel','device_funnel_performance':'AuditDeviceFunnel',
    'daily_conversion_trends':'AuditDailyTrends','acquisition_completeness':'Attribution',
    'quality_indicators':'QualityIndicators','data_coverage':'DataCoverage','window_kpis':'AuditWindowKpis',
    'cohort_sessions':'CohortSessions','user_activity':'UserActivity','session_activity':'SessionActivity'}
SOURCE_KEYS = {
    'events':'No guaranteed event primary key; projected duplicates retained (observed zero).',
    'sessions':'(user_pseudo_id, ga_session_id)',
    'context_sessions':'(user_pseudo_id, ga_session_id)',
    'daily_kpis':'event_date','daily_summary':'event_date','daily_funnel':'(entry_date, stage_order)',
    'ordered_funnel':'stage_order','device_funnel':'(device_category, stage_order)',
    'duckdb_funnel':'(scope, device_category, stage_order); device null for ALL',
    'extracted_dates':'event_date'}


def logical(column):
    if column in TEXT:
        return 'Text','type text'
    if column in DATES:
        return 'Date','type date'
    if column in BOOLS:
        return 'True/False','type logical'
    if column.endswith('_rate'):
        return 'Decimal number (fraction)','type number'
    return 'Whole number (64-bit)','Int64.Type'


def generate(source,package,docs):
    audit=[]
    for file in sorted(source.glob('*.csv')):
        inferred=pd.read_csv(file)
        text=pd.read_csv(file,dtype='string')
        for c in text:
            intended=('Text (never floating point)' if c in ['user_pseudo_id','ga_session_id']
                else 'Whole number (64-bit microseconds)' if c=='event_timestamp'
                else 'Text YYYYMMDD' if c=='event_date' and file.stem=='events'
                else logical(c)[0] if c in DATES or c in BOOLS
                else str(inferred[c].dtype))
            audit.append({'file':file.name,'field':c,'rows':len(text),'csv_inferred_dtype':str(inferred[c].dtype),
                'logical_type_or_observation':intended,'blank_values':int(text[c].isna().sum()),
                'table_primary_key':SOURCE_KEYS[file.stem]})
    pd.DataFrame(audit).to_csv(docs/'source_schema_audit.csv',index=False,encoding='utf-8-sig')
    content=('# Power BI dashboard data dictionary\n\n'
        'Audited locally against the verified January 1–7 output files. `source_schema_audit.csv` records every '
        'source column, inferred CSV dtype, blank count, row count and intended key. CSV has no intrinsic types. '
        'In particular user_pseudo_id is incorrectly inferred as float64: always read source identifiers as text. '
        'Session IDs are also treated as text identifiers conceptually, even if parsable as 64-bit integers. '
        'The dashboard package substitutes integer keys and does not export raw IDs or a reverse mapping. '
        'Surrogates are local to a package, not stable cross-refresh identities.\n\n'
        'All tables below are REAL_GA4_PUBLIC_SAMPLE, with dates Jan 1–7 and context Dec 31–Jan 8 where stated. '
        'See desktop_setup.md for the only permitted relationships. A source event has no guaranteed unique key; '
        'source session tables use the composite user/session key without date.\n\n')
    loader=('// Create a Text parameter named PackageFolder pointing to the package directory.\n'
        '// Create one blank query named LoadCsv with this function:\n'
        '(FileName as text, ColumnTypes as list) as table =>\n'
        'let\n'
        '    Root = Text.TrimEnd(PackageFolder, {"\\", "/"}),\n'
        '    Raw = Csv.Document(File.Contents(Root & "\\" & FileName), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        '    Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),\n'
        '    Blanks = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),\n'
        '    Typed = Table.TransformColumnTypes(Blanks, ColumnTypes, "en-US")\n'
        'in Typed\n\n'
        '// The expressions below are SEPARATE named queries, not one script.\n')
    for name,keys in PRIMARY_KEYS.items():
        frame=pd.read_csv(package/f'{name}.csv')
        role=('dimension; keys only filter their documented fact tables' if name in ['dim_date','dim_device']
              else 'disconnected stage selector' if name=='dim_stage'
              else 'disconnected fixed-window/context audit; no interactive relationships' if name in [
                  'overall_ordered_funnel','device_funnel_performance','daily_conversion_trends','window_kpis',
                  'quality_indicators','data_coverage']
              else 'fact/presence table; dimension filters only, never join to another fact')
        content+=f"## {name}.csv → {MODEL_NAMES[name]}\n\nRows: **{len(frame):,}**. Primary key/grain: **{', '.join(keys)}**. Role: {role}.\n\n"
        content+='| Field | Power BI type | Blank rows | Definition / aggregation rule |\n|---|---|---:|---|\n'
        type_list=[]
        for column in frame:
            if column not in DESCRIPTIONS:
                raise ValueError(f'Undocumented dashboard field: {column}')
            label,m_type=logical(column)
            content+=f'| {column} | {label} | {int(frame[column].isna().sum())} | {DESCRIPTIONS[column]} |\n'
            type_list.append('{"'+column+'", '+m_type+'}')
        content+='\n'
        loader+=f'// Query name: {MODEL_NAMES[name]}\nLoadCsv("{name}.csv", {{'+', '.join(type_list)+'})\n\n'
    content+=('## Aggregation and join rules\n\n'
        'Hide raw numeric columns and use the documented measures. Counts can be added only across disjoint grains. '
        'Users and active sessions are distinct across dates via presence tables. Product-view denominators repeat '
        'across stage rows; event denominators repeat across source/medium rows. Never sum those repeated values '
        'across stages/fields. Ratios are numerator/denominator with blanks for zero denominators. '
        'Unique stage users are nonadditive across dates/devices/stages. Static audit tables have no relationships '
        'and their values must not be displayed as if slicer-responsive. Only DimDate → dated facts and '
        'DimDevice → CohortSessions single-direction relationships are permitted; no fact-to-fact joins.\n')
    (docs/'data_dictionary.md').write_text(content,encoding='utf-8')
    (docs/'import_queries.pq').write_text(loader,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/processed/ga4/20210101_07_verified'))
    parser.add_argument('--package',type=Path,default=Path('powerbi/data/ga4_20210101_07'))
    parser.add_argument('--docs',type=Path,default=Path('powerbi'))
    args=parser.parse_args()
    generate(args.source,args.package,args.docs)
