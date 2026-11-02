# Foundational conversion funnel: single-day workflow

This is the current workflow. The earlier four-stage `productpulse.pipeline` and seven-day SQL remain available for historical demonstrations. They do not include checkout and should not be substituted for the foundation workflow. No dashboard or experiment is run here.

Verified November 2, 2026: the single-day workflow succeeded with ADC and SQL/Python reconciliation. See the [real-data report](../reports/real_data_20210101.md). Existing output directories now contain verified results; use fresh directories for a repeat run.

## Authentication boundary

The earlier access check stopped at `DefaultCredentialsError`, before any BigQuery request. The Google Cloud CLI was not on PATH, no standard Windows ADC file was present, and no real export existed. Do not send credentials in chat or copy them into this repository.

Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install), restart the VS Code terminal, create/select your own query project and enable its BigQuery API. Your account needs permission to run query jobs there (for example BigQuery Job User), plus access to the public source. Quota-project configuration may require Service Usage Consumer permissions. Sandbox availability and quotas are account-dependent. Public data does not eliminate authentication or query-project requirements.

Use Google's [standard local ADC workflow](https://docs.cloud.google.com/bigquery/docs/authentication):

```powershell
gcloud init
$projectId = 'YOUR_PROJECT_ID'
gcloud config set project $projectId
gcloud auth application-default login
gcloud auth application-default set-quota-project $projectId
.\.venv\Scripts\python.exe -m pip install -e ".[bigquery,dev]"
```

The login opens Google's sign-in flow and stores ADC outside the repository. CLI login and ADC are separate; the Python client uses ADC. No service-account key is needed. Credential filenames, raw exports and real analytical outputs are ignored by Git, but always inspect `git status` before committing. Do not print tokens or credential JSON.

## Extract and verify January 1, 2021

```powershell
.\.venv\Scripts\python.exe -m productpulse.bigquery_extract --project $projectId --date 2021-01-01 --output data/raw/ga4/20210101 --max-bytes 1000000000
.\.venv\Scripts\python.exe -m productpulse.foundation --input data/raw/ga4/20210101/events.csv --label ga4 --output data/processed/ga4/20210101
.\.venv\Scripts\python.exe -m productpulse.validate_run --raw-dir data/raw/ga4/20210101 --analysis-dir data/processed/ga4/20210101
```

Run each command only after the previous one succeeds. Every run needs new/empty output directories; choose a fresh run suffix when repeating. The extraction default is one concrete daily shard, not the three-month wildcard. `--max-bytes` caps each executed query; the total across queries can exceed that per-query cap. The client dry-runs all queries first and stops if any estimate exceeds the cap. Quotas/API/permission errors remain possible after authentication. No external integration is established by merely installing the SDK.

The extractor reads actual table metadata and validates required nested field types/modes. It then inventories actual event names, audits repeated session parameter keys, extracts all event names from the one shard, and obtains independent SQL funnel/user aggregates. All events are retained because total users and first-event device should not be inferred from only purchasing events. Repeated ga_session_id parameter keys stop extraction; MAX is not used to conceal ambiguity. Identical event rows are reported and retained, but they do not inflate distinct-user or session-reach measures.

Generated raw files: `events.csv`, `event_inventory.csv`, `sql_funnel.csv`, `sql_user_kpis.csv`, `extraction.json`. The manifest records observed schema, query hashes, job IDs, row counts, bytes and input hash. The metadata schema is an expectation until a successful extraction records it. Missing `begin_checkout` is reported, never inferred from purchase or silently removed. Event inventory is an aggregate and cannot replace event-level input.

The validation command compares input hashes, source/export row counts, unique-user KPIs and overall/device ordered counts and rates. A successful local comparison is necessary, and the November 2, 2026 run passed it against a real extraction. Review job provenance and event coverage as well; provenance files are evidence records, not cryptographic proof of origin.

## Manual export fallback

If local ADC setup is unavailable but you can access the BigQuery console, run `sql/foundation/01_schema.sql`, `02_inventory.sql` and `03_extract.sql` in your own project with GoogleSQL and US location. Inspect estimated bytes before execution. Confirm the schema paths and export the third query's event-level results as CSV. Preserve IDs as strings and reconcile its row count against the inventory sum. Then run foundation on that CSV. Without independent SQL aggregate exports and extraction provenance, `validate_run` is not applicable; record the SQL parity check as pending. Do not manufacture an extraction.json to pass validation.

SQL files 04â€“07 operate on named flat inputs. To inspect complete runnable GoogleSQL without authentication, use Python's `sql_bundle(table_for('2021-01-01'))` from `productpulse.bigquery_extract`; keys `ordered_sessions`, `funnel` and `user_kpis` include their source CTEs. The extractor executes those same texts. The portable core is tested with DuckDB; BigQuery dry-run/execution remains the cloud verification step.

## Definitions and outputs

| Output | Definition |
|---|---|
| summary.json / kpi_summary.md | Total event rows; distinct non-null pseudonyms overall and separately for view_item, add_to_cart, begin_checkout and purchase; provenance/missingness and missing expected events |
| event_reach.csv | Event counts and unordered distinct pseudonyms per event; a user can appear in multiple rows |
| sessions.csv | One eligible (user_pseudo_id, ga_session_id), deterministic entry device, four ordered flags |
| ordered_funnel.csv | Product view â†’ cart â†’ checkout â†’ purchase within a single session, strict timestamp increase; no page_view prerequisite |
| device_funnel.csv | Same session funnel grouped by earliest event's device; lexicographic normalized device breaks timestamp ties |

Funnel conversion = stage sessions / product-view entry sessions. Step conversion = current sessions / previous sessions. Abandoned sessions = previous minus current; abandonment rate = 1 minus step conversion. First-stage step metrics and zero-denominator rates are blank, never invented as zero. CSV rates are fractions; the Markdown summary formats percentages. Distinct users in ordered sessions are provided too, but rates use sessions consistently. Users appearing on multiple devices can occur in multiple device user counts; do not sum them.

Unordered reach includes identified users with missing session IDs; the sequential funnel excludes rows missing either identity component. A purchaser KPI is not a count of orders, transactions, customers or completed ordered funnels. Events in different sessions cannot complete each other's stages. Equal timestamps cannot prove order; later valid events may qualify. Session key is user plus session ID, not session ID alone.

## Source limitations and next expansion

Google's [sample documentation](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset) describes obfuscated data for November 2020 through January 2021, placeholders, and limited internal consistency. Pseudonyms are not people, missing steps may reflect instrumentation, and the one-day boundary truncates sessions. This extract's results must be described as within-shard observations. First-user traffic source is not session campaign attribution; no revenue or causal uplift is inferred. Retention cannot be measured meaningfully with one day.

After an authenticated single-day run and SQL/Python reconciliation pass, expand to a longer explicitly bounded window with an entry-date/boundary policy, validate missing-day coverage and only then proceed to broader product/retention reporting. Dashboard and experiment work stays deferred.
