# Seven-day GA4 workflow and Power BI data contract

The existing single-day workflow remains available and its January 1 outputs are unchanged. The multi-day workflow uses the same cleaning, composite session identity, strict ordered funnel and deterministic entry-device definitions.

## Reproduction

Use the existing project interpreter and working ADC. Dependencies include DuckDB from the development extra for independent validation:

```powershell
uv pip install --python .venv/Scripts/python.exe -e ".[bigquery,dev]"
.\.venv\Scripts\python.exe -m productpulse.bigquery_extract --project productpulse-analytics-2026 --date 2020-12-31 --end-date 2021-01-08 --output data/raw/ga4/NEW_context --max-bytes 1000000000
.\.venv\Scripts\python.exe -m productpulse.multiday --raw-dir data/raw/ga4/NEW_context --output data/processed/ga4/NEW_verified --start 2021-01-01 --end 2021-01-07
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts databricks
```

Run each step only after the preceding step succeeds. Outputs must be new/empty directories. Existing verified real results are in `data/processed/ga4/20210101_07_verified/`. An initial successful local run is retained separately in `20210101_07/`; use the verified directory for integration.

These are daily sharded source tables, not ingestion-time partitions. Literal `_TABLE_SUFFIX BETWEEN '20201231' AND '20210108'` predicates prune the wildcard source. Every selected shard's schema is checked. Every query is dry-run before any data job; the existing 1 GB cap applies per executed query, not the sum. This run's largest estimate was 82,902,193 bytes. No cloud billing, API or IAM settings are changed. Free-tier balance and other project usage are unknown; recorded processed/billed bytes do not establish a monetary charge.

## Calendar activity and session cohort

- Calendar metrics filter exported `event_date` to January 1–7, retaining original source timestamps and IDs. No UTC-to-property-timezone inference is made.
- Eligible identity is `(user_pseudo_id, ga_session_id)`, independent of date. Sessions crossing midnight retain one key. Never group by session ID alone or append the date to identity.
- The cohort includes sessions whose earliest observed timestamp across December 31–January 8 has an exported date in January 1–7. Minimum exported date breaks ties at that timestamp. This is **observed entry**, not proof of actual session start.
- Use all observed context events for each cohort session's four-stage funnel. A January 7 entrant can complete on January 8. A December 31 entrant active on January 1 is counted in calendar activity but excluded from this entry cohort.
- Earliest-event device uses the existing lexicographic normalized-device tie rule. Funnel steps require strictly increasing timestamps; equal timestamps do not establish order. Repeated rows are counted and retained; they cannot independently inflate distinct sessions or establish later steps.
- One adjacent day on each side is required by this workflow; missing dates stop analysis rather than silently filling zeros. All first/last-context-date sessions are flagged as potentially incomplete. This is conservative and cannot detect every session extending beyond context. No timeout, session-start reconstruction or invented identity is introduced.
- Cohort sessions touching January 8 remain included and flagged. Interpret the result as context-observed conversion. Four cohort sessions are flagged in this run, including three product-view sessions and one ordered purchase session. Excluding those four as a sensitivity check gives an ordered funnel of 3,939 → 741 → 189 → 90 (2.28% conversion), versus the inclusive 2.31%. The inclusive result remains the primary definition. More padding could reveal additional events; completeness is not claimed.

January 1 calendar-active sessions remain 2,311. January 1 observed-entry cohort sessions are 2,308 because three sessions entered in December 31 context. This is an explicit denominator distinction, not a change to the saved single-day result. All 22,096 January 1 raw rows match the baseline extraction as a multiset.

## Files and grains

| File | Grain and use |
|---|---|
| `events.csv` | One raw projected event in January 1–7; original date, integer microsecond timestamp, pseudonym/session ID, device, source and medium |
| `sessions.csv` | One observed-entry cohort composite session across all dates; four ordered flags, entry_date, observed date bounds, crossing and incomplete flags |
| `context_sessions.csv` | One composite session across all nine days; use for boundary audits, not seven-day totals |
| `daily_summary.csv` | One calendar/entry date: activity counts, cohort counts, stage session counts, overall ordered conversion, event-weighted attribution missing rates |
| `daily_kpis.csv` | One calendar/entry date: active users/sessions, entry sessions and missing acquisition counts/rates |
| `daily_funnel.csv` | One entry date × stage: counts, distinct ordered users, entry/step conversion and step abandonment |
| `ordered_funnel.csv` | One stage for the entire seven-day entry cohort |
| `device_funnel.csv` | One entry device × stage for the cohort |
| `extracted_dates.csv` | One source event_date × exported row count, including context |
| `duckdb_funnel.csv` | Independent SQL overall/device aggregates for reconciliation |
| `summary.json` | Source hash, query jobs/bytes, quality counts and validation record |
| `kpi_summary.md`, `data_quality.md`, `executive_findings.md` | Calculated local reports |

Raw nine-day files and extraction metadata live under `data/raw/ga4/20210101_07_context/`. Both raw and real processed outputs are ignored by Git. Identifiers are pseudonymous source data; avoid publishing event/session tables as portfolio artifacts.

## Power BI import guidance

Create a calendar dimension covering January 1–7. Relate daily activity by `event_date` and entry cohorts by `entry_date`; retain clear role labels. Import session IDs and user pseudonyms as **Text**, timestamps as **64-bit integers**, dates as **Date**, and flags as Boolean/whole number. Do not let automatic type detection round IDs. CSV rates are fractions; format them as percentages. Blank rates mean undefined denominators, not zero conversion.

Use the wide daily summary for simple trend review or the long daily funnel for stage exploration; avoid joining the two fact tables at an incomplete grain. Do not join raw events directly to device/stage aggregates or sum aggregate tables together: that multiplies counts.

Daily active users and active sessions overlap across dates. Their sums are not seven-day distinct counts. Use `summary.json` window distinct totals or distinct composite keys from the correct fact scope. Daily entry-session counts and stage sessions are additive across entry dates. Distinct users per day, stage or device are not generally additive. Recompute combined rates as summed numerators divided by summed denominators rather than averaging percentages. Entry conversion uses product-view sessions, not all eligible sessions or active users.

Acquisition missingness is event-weighted: normalized NULL/empty/`<Other>`/`(not set)` source or medium values divided by calendar-day events. Source/medium describe exported first-user acquisition and must not be labeled session campaign attribution. No dashboard or DAX model has been implemented.

## Validation

BigQuery validates live schemas and independently exports the all-context ordered funnel and user KPIs. Python reconciles those before selecting the cohort. DuckDB independently executes the existing portable SQL session core, checks every cohort session flag and overall/device aggregates, and independently checks daily activity, daily entry/stage counts and daily funnel rates. Source audit, event inventory and export counts reconcile. Tests cover cross-midnight keys, context boundaries, duplicate/missing values and ties. The obfuscated sample and finite context remain analytical limitations even when all checks pass.
