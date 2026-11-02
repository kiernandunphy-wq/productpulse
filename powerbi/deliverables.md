# Exact deliverables and validation record

Prepared November 2, 2026 from the existing real seven-day analysis. No new BigQuery queries were submitted and no cloud settings were changed. No `.pbix` exists from this phase. The package is not synthetic; real-source provenance checks reject fixture inputs. Package-local integer surrogates replace raw user/session identifiers, but the row-level package remains private and Git-ignored.

## Generated package

Directory: `powerbi/data/ga4_20210101_07/` (relative to repository root).

| Exact file | Rows | Primary key |
|---|---:|---|
| dim_date.csv | 7 | date |
| dim_device.csv | 3 | device_category |
| dim_stage.csv | 4 | stage_order |
| daily_kpis.csv | 7 | activity_date |
| overall_ordered_funnel.csv | 4 | stage_order |
| device_funnel_performance.csv | 12 | device_category, stage_order |
| daily_conversion_trends.csv | 28 | entry_date, stage_order |
| acquisition_completeness.csv | 14 | activity_date, attribution_field |
| quality_indicators.csv | 14 | indicator |
| data_coverage.csv | 9 | date |
| window_kpis.csv | 1 | dataset_id |
| cohort_sessions.csv | 26,328 | session_key |
| user_activity.csv | 24,157 | activity_date, user_key |
| session_activity.csv | 26,374 | activity_date, session_key |

- `powerbi/data/ga4_20210101_07/manifest.json` ? real-source marker, file hashes, row counts, primary keys, source hashes and packaging validation. Desktop/PBIX status is explicitly false.

## New implementation, documentation and presentation files

- `src/productpulse/dashboard_export.py`
- `scripts/build_powerbi_contract.py`
- `tests/test_dashboard_export.py`
- `powerbi/desktop_setup.md`
- `powerbi/data_dictionary.md`
- `powerbi/source_schema_audit.csv`
- `powerbi/import_queries.pq`
- `powerbi/measures.dax`
- `powerbi/report_design.md`
- `powerbi/theme.json`
- `powerbi/deliverables.md` (this inventory)
- `reports/portfolio_dashboard_summary.md`

Updated existing files: `README.md`, `powerbi/README.md`, `.gitignore` (ignores `powerbi/data/`). No existing single-day/seven-day analytical output or executive report was modified. Temporary test packages were confined to pytest temporary directories and are not deliverables.

## Validation outcomes

- Full suite: **45 tests passed in 30.09 seconds** (34 existing + 11 new), no warnings in that run. Ruff: **All checks passed** for `src tests scripts databricks`.
- All 14 delivered CSVs were checked again against the current transformation and verified source files; CSV hashes and source hashes match. CSV round-trips preserve values and intentional blank rates.
- Reconciled 245,209 window events, 22,847 distinct active users, 26,331 distinct active sessions, 26,328 entry-cohort sessions, and ordered stage counts 3,942 / 743 / 190 / 91. Every cohort date/device slice agrees with existing analytical outputs.
- Seven daily user-presence sets contain 24,157 rows but only 22,847 distinct users. Session-presence sets contain 26,374 rows but only 26,331 distinct sessions. These differences demonstrate why SUM of daily distinct counts is invalid.
- All table primary keys are non-null and unique. Documented dimension joins preserve row counts and have no orphan keys. No fact-to-fact or many-to-many join is part of the proposed model.
- Conversion/step/abandonment rates match explicit integer denominators, including zero-denominator blanks. Daily attribution numerator/denominator checks agree with normalized source events.
- Tampered dimension keys, fact duplicates, counts, rates and attribution values fail validation. Synthetic provenance is rejected. Existing package outputs are protected from overwrite.
- Original real-data SQL reconciliation is retained; the exporter also checks the saved independent DuckDB funnel reference. No fresh cloud job is necessary for this phase.

## Manual Power BI Desktop steps still required

1. Open Desktop and create a blank report; point the `PackageFolder` parameter at the full local package path above. Follow `desktop_setup.md` to import the 14 CSVs with the exact model-table names and explicit types (or use the separate typed expressions in `import_queries.pq`). Importing the existing package does not require regeneration.
2. Remove auto-detected relationships and create only the six documented active, single-direction dimension relationships. Keep stage, quality, coverage and audit tables disconnected. Mark the date table; hide keys and audit tables after checks.
3. Add each measure from `measures.dax` separately, import `theme.json` if desired, and build Executive Overview, Customer Behavior, and Data Quality & Methodology per `report_design.md`. Configure device interactions to affect cohort visuals only.
4. Run every acceptance check in `desktop_setup.md`, including full totals, January 1, device counts, multi-date distinct counts, missing attribution denominators, undefined rates, boundary flags, reset behavior and accessibility. Power Query, DAX engine execution, visuals and interactions are **not yet verified**.
5. Only after successful checks, save an actual `ProductPulse.pbix`, record Desktop version and acceptance outcomes, and capture screenshots for the portfolio. No publication or Power BI service deployment was performed.
