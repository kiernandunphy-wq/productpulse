"""Single-day authenticated GA4 extraction. Never handles or prints credential contents."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DATASET = 'bigquery-public-data.ga4_obfuscated_sample_ecommerce'
SQL_DIR = Path(__file__).resolve().parents[2] / 'sql' / 'foundation'
REQUIRED_PATHS = {
    'event_date': ('STRING', 'NULLABLE'), 'event_timestamp': ('INTEGER', 'NULLABLE'),
    'event_name': ('STRING', 'NULLABLE'), 'user_pseudo_id': ('STRING', 'NULLABLE'),
    'event_params': ('RECORD', 'REPEATED'), 'event_params.key': ('STRING', 'NULLABLE'),
    'event_params.value.int_value': ('INTEGER', 'NULLABLE'),
    'traffic_source.source': ('STRING', 'NULLABLE'), 'traffic_source.medium': ('STRING', 'NULLABLE'),
    'device.category': ('STRING', 'NULLABLE')}


def table_for(day):
    parsed = datetime.strptime(day, '%Y-%m-%d').date()
    if not datetime(2020, 11, 1).date() <= parsed <= datetime(2021, 1, 31).date():
        raise ValueError('Date must be in sample range 2020-11-01 through 2021-01-31')
    return f'{DATASET}.events_{parsed:%Y%m%d}'


def validate_schema(schema):
    actual = {}

    def visit(fields, prefix=''):
        for field in fields:
            path = prefix + field.name
            actual[path] = (field.field_type, field.mode)
            visit(field.fields, path + '.')

    visit(schema)
    mismatches = {path: {'expected': expected, 'actual': actual.get(path)}
                  for path, expected in REQUIRED_PATHS.items() if actual.get(path) != expected}
    if mismatches:
        raise ValueError(f'Schema contract mismatch: {mismatches}')
    return actual


def query_text(filename, table, sql_dir=SQL_DIR):
    return (Path(sql_dir) / filename).read_text(encoding='utf-8').replace(
        f'{DATASET}.events_20210101', table)


def sql_bundle(table, sql_dir=SQL_DIR):
    extract = query_text('03_extract.sql', table, sql_dir)
    # Match cleaning's missing-identity and event-name policy for SQL/Python parity.
    normalize = lambda col: f"NULLIF(NULLIF(NULLIF(TRIM({col}),''),'<Other>'),'(not set)')"
    flat = (f'WITH raw AS ({extract}) SELECT * REPLACE '
            f'({normalize("user_pseudo_id")} AS user_pseudo_id, '
            f'{normalize("event_name")} AS event_name) FROM raw')
    core = query_text('04_ordered_sessions.sql', table, sql_dir)
    sessions = f'WITH events AS ({flat}), ' + core.replace('WITH eligible AS', 'eligible AS', 1)
    summary = query_text('05_funnel_summary.sql', table, sql_dir)
    return {'extract': extract, 'inventory': query_text('02_inventory.sql', table, sql_dir),
            'user_kpis': f'WITH events AS ({flat}) ' + query_text('07_user_kpis.sql', table, sql_dir),
            'ordered_sessions': sessions,
            'funnel': f'WITH ordered_sessions AS ({sessions}), ' + summary.replace('WITH stage_counts AS', 'stage_counts AS', 1),
            'audit': f'''SELECT COUNT(*) AS event_rows,
              COUNTIF((SELECT COUNT(*) FROM UNNEST(event_params) WHERE key='ga_session_id')>1) AS duplicate_session_keys
              FROM `{table}`'''}


def range_bundle(start, end, sql_dir=SQL_DIR):
    """Prune date-sharded tables with a literal suffix filter (not ingestion partitions)."""
    first, last = table_for(start), table_for(end)
    if start > end:
        raise ValueError('Start date must not exceed end date')
    source = (f"(SELECT * FROM `{DATASET}.events_*` WHERE _TABLE_SUFFIX "
              f"BETWEEN '{first[-8:]}' AND '{last[-8:]}')")
    return {name: sql.replace(f'`{first}`', source)
            for name, sql in sql_bundle(first, sql_dir).items()}


def execute(project, day, output, max_bytes, sql_dir=SQL_DIR, end_date=None):
    import google.auth
    from google.cloud import bigquery
    if max_bytes <= 0:
        raise ValueError('Maximum bytes must be positive')
    table = table_for(day)
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    client = bigquery.Client(project=project, credentials=credentials, location='US')
    schema = validate_schema(client.get_table(table).schema)
    queries = sql_bundle(table, sql_dir)
    if end_date:
        from datetime import timedelta
        queries = range_bundle(day, end_date, sql_dir)
        current = datetime.strptime(day, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        while current <= end:
            validate_schema(client.get_table(table_for(current.isoformat())).schema)
            current += timedelta(days=1)
    # Dry-run every query before submitting any data jobs. Cap bytes per query.
    estimates = {}
    for name, sql in queries.items():
        job = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        estimates[name] = job.total_bytes_processed or 0
        if estimates[name] > max_bytes:
            raise ValueError(f'{name} exceeds maximum bytes; no data queries submitted')
    directory = Path(output)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Output must be a new/empty directory')
    records = []

    def fetch(name):
        job = client.query(queries[name], job_config=bigquery.QueryJobConfig(maximum_bytes_billed=max_bytes))
        result = job.result()
        columns = [field.name for field in result.schema]
        rows = [dict(row) for row in result]
        records.append({'name': name, 'job_id': job.job_id, 'rows': len(rows),
                        'bytes_processed': job.total_bytes_processed,
                        'bytes_billed': getattr(job, 'total_bytes_billed', None),
                        'cache_hit': getattr(job, 'cache_hit', None),
                        'sql_sha256': hashlib.sha256(queries[name].encode()).hexdigest()})
        return columns, rows

    _, audit = fetch('audit')
    if audit[0]['duplicate_session_keys']:
        raise ValueError('Repeated ga_session_id keys found; extraction stopped for investigation')
    results = {name: fetch(name) for name in ['inventory', 'extract', 'funnel', 'user_kpis']}
    if len(results['extract'][1]) != audit[0]['event_rows']:
        raise ValueError('Export count mismatch')
    import pandas as pd
    directory.mkdir(parents=True, exist_ok=True)
    names = {'inventory': 'event_inventory.csv', 'extract': 'events.csv',
             'funnel': 'sql_funnel.csv', 'user_kpis': 'sql_user_kpis.csv'}
    for name, (columns, rows) in results.items():
        pd.DataFrame(rows, columns=columns).to_csv(directory / names[name], index=False)
    manifest = {'source_table': table, 'queried_at_utc': datetime.now(timezone.utc).isoformat(),
                'schema': schema, 'audit': audit[0], 'jobs': records,
                'dry_run_bytes': estimates, 'maximum_bytes_per_query': max_bytes,
                'input_sha256': hashlib.sha256((directory / 'events.csv').read_bytes()).hexdigest()}
    if end_date:
        manifest['source_table'] = f'{DATASET}.events_*'
        manifest['date_start'] = day
        manifest['date_end'] = end_date
    (directory / 'extraction.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return {'source_table': manifest['source_table'], 'event_rows': audit[0]['event_rows'], 'output': str(directory)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Your query execution project, not bigquery-public-data')
    parser.add_argument('--date', default='2021-01-01')
    parser.add_argument('--end-date', help='Inclusive last shard; omitted preserves single-day behavior')
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-bytes', type=int, default=1_000_000_000)
    parser.add_argument('--sql-dir', type=Path, default=SQL_DIR)
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.project, args.date, args.output, args.max_bytes, args.sql_dir,
                                 end_date=args.end_date), indent=2))
    except ValueError as exc:
        parser.exit(1, f'Extraction stopped: {exc}\n')
    except Exception as exc:
        # Avoid logging arbitrary SDK exceptions that might contain authentication details.
        parser.exit(1, f'Extraction stopped ({type(exc).__name__}). No results claimed. '
                    'Check ADC, project permissions, schema, dry-run budget and docs/foundation.md.\n')


if __name__ == '__main__':
    main()
