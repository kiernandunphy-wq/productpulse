# Foundation audit and development status

## Seven-day verification ? November 2, 2026

The January 1?7 extension succeeded with December 31/January 8 context: 245,209 window events, 22,847 distinct users, 26,328 observed-entry cohort sessions, and a 3,942 ? 743 ? 190 ? 91 ordered funnel. Real BigQuery context and DuckDB cohort/daily reconciliation passed. The single-day baseline below remains intact. See [seven-day findings](../reports/real_data_20210101_07.md) and [workflow/data contract](multiday.md).

## Single-day verification ? November 2, 2026

The authenticated single-day pipeline is now verified: 22,096 real GA4 events, 2,311 eligible sessions, and ordered funnel 321 ? 63 ? 20 ? 10. ADC, BigQuery API, source metadata, query execution and SQL/Python reconciliation passed. All 27 tests and Ruff pass. See the [complete run report](../reports/real_data_20210101.md). No single-day blocker remains; next is bounded multi-day extraction with session-boundary validation.

The sections below preserve the earlier audit and its historical blockers; they are superseded by the run report above.

## Repository audit

Existing work was retained. The initial implementation contained modular cleaning, a four-stage ordered session funnel, cohort tables, a CLI, notebooks, synthetic CSV outputs, a seeded experiment, BigQuery SQL and reporting guidance. Baseline verification: **11 tests passed in 3.68 seconds**. No linter was installed/configured at that point. No authentic raw export was present.

| Area | Audited state / current state |
|---|---|
| Existing cleaning / four-stage pipeline | Implemented and locally tested with fixtures; checkout absent; preserved as legacy workflow |
| Existing notebooks | Earlier local execution recorded; not rerun or changed in this phase |
| Existing experiment | Earlier synthetic implementation retained; no new experiment analysis or dashboard work performed |
| Retention | Implemented for observed activity; not suitable for single-day interpretation; real source coverage unverified |
| Power BI / Databricks / publication | Guidance/source artifacts exist; platform integrations and public deployment unverified |
| Live GA4 schema and event names | **Not confirmed**: no ADC; documentation and schema contracts are not live observations |
| Foundation extraction | New ADC-based single-shard client, metadata contract, inventory, duplicate-key audit, dry-run budget cap and export provenance; syntax/guardrails tested locally, successful cloud execution untested |
| Foundation funnel | Implemented: unordered user KPIs, sequential session funnel including checkout, conversion/abandonment and device comparisons; tested with synthetic fixtures |
| SQL independence | Portable SQL core executed in DuckDB, matching Python counts/rates and user KPIs; composed GoogleSQL parsed locally; BigQuery engine parity pending |
| Reconciliation | File/hash/row/KPI/SQL funnel comparisons implemented and tested with local synthetic artifacts, including tampering failures |

## Actual verification results

- Final current suite: **27 tests passed in 5.67 seconds**, no warnings in that run.
- Ruff: **All checks passed** for `src tests scripts databricks`. Configuration checks syntax/undefined names and related correctness errors; it is not a comprehensive style/format audit. Databricks' injected `display` has a documented file-specific undefined-name exception.
- Tests cover missing identities, required columns, invalid dates/numeric IDs, duplicates, shared session IDs, cross-session and out-of-order events, timestamp ties, valid later events, zero denominators, absent checkout, device comparisons, SQL/Python parity and reconciliation failure detection.
- SDK tests use mocks for schema acceptance/rejection, budget enforcement and repeated session-parameter rejection. They do not establish authentication or BigQuery integration success.
- The live access attempt returned **DefaultCredentialsError**, before client construction/query submission. No Google Cloud CLI was found on PATH, standard local ADC was absent, and no credential environment setting was present. No tokens or credential contents were printed.
- Synthetic fixture only: **21 event rows**, **4 distinct identified users**, **5 eligible sessions**, **1 projected duplicate**, **4 session-ineligible rows**. Ordered session counts: **4 Ã¢â€ â€™ 4 Ã¢â€ â€™ 2 Ã¢â€ â€™ 2** (product view, cart, checkout, purchase), giving **50%** ordered session conversion. These are software-check results, not store findings.

During development, independent SQL testing exposed null abandonment counts on empty input. SQL and Python now agree on zero lost sessions with undefined rates. Local GoogleSQL syntax checks also cover assembled query CTEs; cloud schema resolution still requires a live run.

## Blocker and next phase

The first real-data end-to-end run is **not complete**. The required next external step is user sign-in through standard Google ADC and access to a BigQuery query project. Follow [foundation.md](foundation.md), then run single-day extraction, local analysis and independent reconciliation in that order. Do not claim live schema/event discovery or publish real numerical findings until those steps succeed. After reconciliation, extend the bounded source window and validate boundary/missing-day policy. Dashboard and simulated experimentation phases remain deferred.
