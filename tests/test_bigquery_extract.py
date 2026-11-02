"""Unit tests only: SDK calls are mocked, no cloud integration is asserted."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from google.cloud.bigquery import SchemaField
from productpulse.bigquery_extract import REQUIRED_PATHS, execute, validate_schema, sql_bundle, table_for
import sqlglot


def test_composed_google_sql_parses_locally():
    # Syntax check only: no BigQuery schema resolution, permissions or execution is verified.
    for text in sql_bundle(table_for('2021-01-01')).values():
        assert sqlglot.parse_one(text, read='bigquery') is not None


def schema_fields():
    tree = {}
    for path, (kind, mode) in REQUIRED_PATHS.items():
        branch = tree
        pieces = path.split('.')
        for piece in pieces:
            branch = branch.setdefault(piece, {})
        branch['_type'] = kind
        branch['_mode'] = mode

    def build(tree):
        return [SchemaField(name, node.get('_type', 'RECORD'), mode=node.get('_mode', 'NULLABLE'),
            fields=build({key: value for key, value in node.items() if not key.startswith('_')}))
            for name, node in tree.items()]

    return build(tree)


def test_schema_contract_accepts_expected_nested_fields():
    schema = validate_schema(schema_fields())
    assert schema['event_params'] == ('RECORD', 'REPEATED')
    assert schema['event_params.value.int_value'] == ('INTEGER', 'NULLABLE')


def test_dry_run_budget_stops_before_data_jobs(tmp_path):
    client = Mock()
    client.get_table.return_value = SimpleNamespace(schema=schema_fields())
    client.query.return_value = SimpleNamespace(total_bytes_processed=101)
    with patch('google.auth.default', return_value=(Mock(), None)), patch('google.cloud.bigquery.Client', return_value=client):
        with pytest.raises(ValueError, match='maximum bytes'):
            execute('unit-test-project', '2021-01-01', tmp_path / 'output', 100)
    assert all(call.kwargs['job_config'].dry_run for call in client.query.call_args_list)
    assert not (tmp_path / 'output').exists()


def test_bad_schema_stops_before_query(tmp_path):
    client = Mock()
    client.get_table.return_value = SimpleNamespace(schema=[])
    with patch('google.auth.default', return_value=(Mock(), None)), patch('google.cloud.bigquery.Client', return_value=client):
        with pytest.raises(ValueError, match='Schema contract'):
            execute('unit-test-project', '2021-01-01', tmp_path / 'output', 100)
    client.query.assert_not_called()


def test_duplicate_session_parameters_stop_before_export(tmp_path):
    client = Mock()
    client.get_table.return_value = SimpleNamespace(schema=schema_fields())

    class Rows(list):
        schema = [SimpleNamespace(name='event_rows'), SimpleNamespace(name='duplicate_session_keys')]

    def query(sql, job_config):
        if job_config.dry_run:
            return SimpleNamespace(total_bytes_processed=1)
        return SimpleNamespace(result=lambda: Rows([{'event_rows': 10, 'duplicate_session_keys': 1}]),
                               job_id='mock-only', total_bytes_processed=1)

    client.query.side_effect = query
    with patch('google.auth.default', return_value=(Mock(), None)), patch('google.cloud.bigquery.Client', return_value=client):
        with pytest.raises(ValueError, match='Repeated ga_session_id'):
            execute('unit-test-project', '2021-01-01', tmp_path / 'output', 100)
    assert not (tmp_path / 'output').exists()


def test_range_budget_and_all_shard_schema_checks(tmp_path):
    client = Mock()
    client.get_table.return_value = SimpleNamespace(schema=schema_fields())
    client.query.return_value = SimpleNamespace(total_bytes_processed=101)
    with patch('google.auth.default', return_value=(Mock(), None)), patch('google.cloud.bigquery.Client', return_value=client):
        with pytest.raises(ValueError, match='maximum bytes'):
            execute('unit-test-project','2021-01-01',tmp_path/'range',100,end_date='2021-01-07')
    assert {call.args[0] for call in client.get_table.call_args_list} == {
        table_for(f'2021-01-{day:02}') for day in range(1,8)}
    assert all(call.kwargs['job_config'].dry_run for call in client.query.call_args_list)
    assert "_TABLE_SUFFIX BETWEEN '20210101' AND '20210107'" in client.query.call_args.args[0]
    assert not (tmp_path/'range').exists()


def test_later_shard_schema_failure_stops_before_queries(tmp_path):
    client = Mock()
    client.get_table.side_effect = [SimpleNamespace(schema=schema_fields()),
                                    SimpleNamespace(schema=schema_fields()),SimpleNamespace(schema=[])]
    with patch('google.auth.default', return_value=(Mock(), None)), patch('google.cloud.bigquery.Client', return_value=client):
        with pytest.raises(ValueError,match='Schema contract'):
            execute('unit-test-project','2021-01-01',tmp_path/'range',100,end_date='2021-01-07')
    client.query.assert_not_called()
