"""Checkout-inclusive foundation workflow, separate from legacy four-stage outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from .cleaning import clean_events

STEPS = ['view_item', 'add_to_cart', 'begin_checkout', 'purchase']


def ordered_sessions(events):
    """Earliest valid next event per user/session. Ties never establish order."""
    rows = []
    eligible = events.loc[events.eligible_session].sort_values('event_timestamp', kind='stable')
    for (user, sid), group in eligible.groupby(['user_pseudo_id', 'ga_session_id']):
        # For tied entry events choose a lexicographic device deterministically.
        first_time = group.event_timestamp.min()
        device = sorted(group.loc[group.event_timestamp.eq(first_time), 'device_category'])[0]
        row = {'user_pseudo_id': user, 'ga_session_id': sid, 'device_category': device}
        previous = None
        reachable = True
        for step in STEPS:
            times = group.loc[group.event_name.eq(step), 'event_timestamp']
            if previous is not None:
                times = times[times > previous]
            reachable = reachable and not times.empty
            row[step] = int(reachable)
            if reachable:
                previous = int(times.min())
        rows.append(row)
    return pd.DataFrame(rows, columns=['user_pseudo_id', 'ga_session_id', 'device_category', *STEPS])


def summarize(sessions):
    counts = [int(sessions[step].sum()) for step in STEPS]
    rows = []
    for index, (step, count) in enumerate(zip(STEPS, counts)):
        previous = counts[index-1] if index else None
        rows.append({'stage': step, 'stage_order': index+1, 'sessions': count,
            'unique_users': int(sessions.loc[sessions[step].eq(1), 'user_pseudo_id'].nunique()),
            'conversion_from_entry': count/counts[0] if counts[0] else None,
            'conversion_from_previous': count/previous if previous else None,
            'abandoned_sessions': previous-count if previous is not None else None,
            'abandonment_rate': 1-count/previous if previous else None})
    table = pd.DataFrame(rows)
    for column in ['conversion_from_entry', 'conversion_from_previous', 'abandoned_sessions', 'abandonment_rate']:
        table[column] = pd.to_numeric(table[column])
    return table


def analyze_events(events):
    """Unordered reach includes missing-session users; sequential metrics do not."""
    sessions = ordered_sessions(events)
    reach = events.groupby('event_name').agg(event_count=('event_name', 'size'),
        unique_users=('user_pseudo_id', 'nunique')).reset_index()
    devices = []
    for device, group in sessions.groupby('device_category'):
        table = summarize(group)
        table.insert(0, 'device_category', device)
        devices.append(table)
    funnel = summarize(sessions)
    device_table = pd.concat(devices, ignore_index=True) if devices else pd.DataFrame(
        columns=['device_category', *funnel.columns])
    kpis = {'unique_users': int(events.user_pseudo_id.nunique()),
            'event_count': len(events), 'eligible_sessions': len(sessions)}
    for name, step in zip(['product_viewers', 'add_to_cart_users', 'checkout_starters', 'purchasers'], STEPS):
        kpis[name] = int(events.loc[events.event_name.eq(step), 'user_pseudo_id'].nunique())
    kpis['ordered_session_conversion'] = (int(sessions.purchase.sum()) /
        int(sessions.view_item.sum())) if sessions.view_item.sum() else None
    return {'sessions': sessions, 'ordered_funnel': funnel,
            'device_funnel': device_table, 'event_reach': reach}, kpis


def run(input_path, output, label):
    raw = pd.read_csv(input_path, dtype='string')
    events, quality = clean_events(raw)
    if events.empty:
        raise ValueError('Input has no events; check extraction and export completeness')
    tables, kpis = analyze_events(events)
    directory = Path(output)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Output directory must be empty; use a new run directory')
    directory.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(directory / f'{name}.csv', index=False)
    summary = {'label': label, 'input_sha256': hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
        'quality': quality, 'kpis': kpis,
        'date_min': str(events.event_date.min().date()), 'date_max': str(events.event_date.max().date()),
        'missing_expected_events': [step for step in STEPS if not events.event_name.eq(step).any()],
        'definition': 'view_item > add_to_cart > begin_checkout > purchase, strictly increasing timestamps within user/session',
        'unordered_kpis': 'distinct non-null pseudonyms per event; not sequential; includes missing-session users',
        'device_policy': 'earliest session event; lexicographic device on timestamp ties'}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    stage_report = '\n\n| Stage | Ordered sessions | Distinct users in ordered sessions | Conversion from entry | Step abandonment |\n|---|---:|---:|---:|---:|\n'
    for row in tables['ordered_funnel'].itertuples():
        conversion = f'{row.conversion_from_entry:.2%}' if pd.notna(row.conversion_from_entry) else 'N/A'
        abandonment = f'{row.abandonment_rate:.2%}' if pd.notna(row.abandonment_rate) else 'N/A'
        stage_report += f'| {row.stage} | {row.sessions} | {row.unique_users} | {conversion} | {abandonment} |\n'
    (directory / 'kpi_summary.md').write_text(
        f'# KPI summary: {label.upper()}\n\n' + '\n'.join(f'- {key}: {value}' for key, value in kpis.items()) +
        '\n\nUser KPIs are unordered distinct pseudonyms. Funnel rates are ordered sessions. '
        'Missing events do not justify removing stages. No causal inference is supported.\n' + stage_report, encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--label', required=True, choices=['fixture', 'ga4'])
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, args.label), indent=2))


if __name__ == '__main__':
    main()
