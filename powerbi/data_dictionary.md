# Power BI dashboard data dictionary

Audited locally against the verified January 1–7 output files. `source_schema_audit.csv` records every source column, inferred CSV dtype, blank count, row count and intended key. CSV has no intrinsic types. In particular user_pseudo_id is incorrectly inferred as float64: always read source identifiers as text. Session IDs are also treated as text identifiers conceptually, even if parsable as 64-bit integers. The dashboard package substitutes integer keys and does not export raw IDs or a reverse mapping. Surrogates are local to a package, not stable cross-refresh identities.

All tables below are REAL_GA4_PUBLIC_SAMPLE, with dates Jan 1–7 and context Dec 31–Jan 8 where stated. See desktop_setup.md for the only permitted relationships. A source event has no guaranteed unique key; source session tables use the composite user/session key without date.

## dim_date.csv → DimDate

Rows: **7**. Primary key/grain: **date**. Role: dimension; keys only filter their documented fact tables.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| date | Date | 0 | Dimension or coverage exported calendar date. |

## dim_device.csv → DimDevice

Rows: **3**. Primary key/grain: **device_category**. Role: dimension; keys only filter their documented fact tables.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| device_category | Text | 0 | Normalized device from earliest session event; lexicographic device on timestamp ties. |

## dim_stage.csv → DimStage

Rows: **4**. Primary key/grain: **stage_order**. Role: disconnected stage selector.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| stage_order | Whole number (64-bit) | 0 | Ordered stage index 1=view, 2=cart, 3=checkout, 4=purchase; never additive. |
| stage | Text | 0 | Source event name corresponding to the ordered stage. |
| stage_label | Text | 0 | Human-readable ordered funnel stage; sort by stage_order. |

## daily_kpis.csv → DailyKpis

Rows: **7**. Primary key/grain: **activity_date**. Role: fact/presence table; dimension filters only, never join to another fact.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| activity_date | Date | 0 | Exported calendar date of observed activity; not inferred from UTC timestamp. |
| event_count | Whole number (64-bit) | 0 | Calendar-window event rows, with duplicates retained. |
| daily_active_users | Whole number (64-bit) | 0 | Distinct non-null pseudonyms observed on that day; nonadditive across dates. |
| daily_active_sessions | Whole number (64-bit) | 0 | Distinct eligible composite session keys active on that day; nonadditive across dates. |
| entry_cohort_sessions | Whole number (64-bit) | 0 | Sessions with observed entry date in the row/window; additive across entry dates. |
| missing_source_events | Whole number (64-bit) | 0 | Calendar events with normalized Unknown first-user acquisition source. |
| missing_source_rate | Decimal number (fraction) | 0 | missing_source_events / event_count; event-weighted, not user-weighted. |
| missing_medium_events | Whole number (64-bit) | 0 | Calendar events with normalized Unknown first-user acquisition medium. |
| missing_medium_rate | Decimal number (fraction) | 0 | missing_medium_events / event_count; event-weighted, not user-weighted. |

## overall_ordered_funnel.csv → AuditOverallFunnel

Rows: **4**. Primary key/grain: **stage_order**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| stage | Text | 0 | Source event name corresponding to the ordered stage. |
| stage_order | Whole number (64-bit) | 0 | Ordered stage index 1=view, 2=cart, 3=checkout, 4=purchase; never additive. |
| ordered_sessions | Whole number (64-bit) | 0 | Eligible cohort sessions reaching this stage in strict timestamp order. |
| ordered_unique_users | Whole number (64-bit) | 0 | Distinct pseudonyms reaching the ordered stage; nonadditive across dates/devices/stages. |
| conversion_from_product_view_rate | Decimal number (fraction) | 0 | ordered_sessions / product_view_denominator; undefined denominator is blank. |
| step_conversion_rate | Decimal number (fraction) | 1 | ordered_sessions / previous_stage_denominator; first-stage/zero denominator is blank. |
| abandoned_sessions | Whole number (64-bit) | 1 | previous_stage_denominator minus ordered_sessions; blank for first stage. |
| step_abandonment_rate | Decimal number (fraction) | 1 | 1 minus step_conversion_rate; undefined rates remain blank. |
| product_view_denominator | Whole number (64-bit) | 0 | Product-view sessions in the same date/device scope; repeated across stage rows. |
| previous_stage_denominator | Whole number (64-bit) | 1 | Previous ordered-stage sessions in same scope; blank for stage 1. |
| stage_label | Text | 0 | Human-readable ordered funnel stage; sort by stage_order. |

## device_funnel_performance.csv → AuditDeviceFunnel

Rows: **12**. Primary key/grain: **device_category, stage_order**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| device_category | Text | 0 | Normalized device from earliest session event; lexicographic device on timestamp ties. |
| stage | Text | 0 | Source event name corresponding to the ordered stage. |
| stage_order | Whole number (64-bit) | 0 | Ordered stage index 1=view, 2=cart, 3=checkout, 4=purchase; never additive. |
| ordered_sessions | Whole number (64-bit) | 0 | Eligible cohort sessions reaching this stage in strict timestamp order. |
| ordered_unique_users | Whole number (64-bit) | 0 | Distinct pseudonyms reaching the ordered stage; nonadditive across dates/devices/stages. |
| conversion_from_product_view_rate | Decimal number (fraction) | 0 | ordered_sessions / product_view_denominator; undefined denominator is blank. |
| step_conversion_rate | Decimal number (fraction) | 3 | ordered_sessions / previous_stage_denominator; first-stage/zero denominator is blank. |
| abandoned_sessions | Whole number (64-bit) | 3 | previous_stage_denominator minus ordered_sessions; blank for first stage. |
| step_abandonment_rate | Decimal number (fraction) | 3 | 1 minus step_conversion_rate; undefined rates remain blank. |
| product_view_denominator | Whole number (64-bit) | 0 | Product-view sessions in the same date/device scope; repeated across stage rows. |
| previous_stage_denominator | Whole number (64-bit) | 3 | Previous ordered-stage sessions in same scope; blank for stage 1. |
| stage_label | Text | 0 | Human-readable ordered funnel stage; sort by stage_order. |

## daily_conversion_trends.csv → AuditDailyTrends

Rows: **28**. Primary key/grain: **entry_date, stage_order**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| entry_date | Date | 0 | Exported date at earliest observed cohort timestamp across context; minimum date on ties. |
| stage | Text | 0 | Source event name corresponding to the ordered stage. |
| stage_order | Whole number (64-bit) | 0 | Ordered stage index 1=view, 2=cart, 3=checkout, 4=purchase; never additive. |
| ordered_sessions | Whole number (64-bit) | 0 | Eligible cohort sessions reaching this stage in strict timestamp order. |
| ordered_unique_users | Whole number (64-bit) | 0 | Distinct pseudonyms reaching the ordered stage; nonadditive across dates/devices/stages. |
| conversion_from_product_view_rate | Decimal number (fraction) | 0 | ordered_sessions / product_view_denominator; undefined denominator is blank. |
| step_conversion_rate | Decimal number (fraction) | 7 | ordered_sessions / previous_stage_denominator; first-stage/zero denominator is blank. |
| abandoned_sessions | Whole number (64-bit) | 7 | previous_stage_denominator minus ordered_sessions; blank for first stage. |
| step_abandonment_rate | Decimal number (fraction) | 7 | 1 minus step_conversion_rate; undefined rates remain blank. |
| product_view_denominator | Whole number (64-bit) | 0 | Product-view sessions in the same date/device scope; repeated across stage rows. |
| previous_stage_denominator | Whole number (64-bit) | 7 | Previous ordered-stage sessions in same scope; blank for stage 1. |
| stage_label | Text | 0 | Human-readable ordered funnel stage; sort by stage_order. |

## acquisition_completeness.csv → Attribution

Rows: **14**. Primary key/grain: **activity_date, attribution_field**. Role: fact/presence table; dimension filters only, never join to another fact.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| activity_date | Date | 0 | Exported calendar date of observed activity; not inferred from UTC timestamp. |
| event_denominator | Whole number (64-bit) | 0 | Calendar event rows for this date and selected field; repeated for source/medium. |
| missing_events | Whole number (64-bit) | 0 | Events whose selected acquisition field is Unknown under existing normalization. |
| missing_rate | Decimal number (fraction) | 0 | missing_events / event_denominator; do not average across dates. |
| attribution_field | Text | 0 | source or medium; separate field scopes, not unique missing-event categories. |
| available_events | Whole number (64-bit) | 0 | event_denominator minus missing_events for the selected field. |
| completeness_rate | Decimal number (fraction) | 0 | available_events / event_denominator; field-scoped event completeness. |

## quality_indicators.csv → QualityIndicators

Rows: **14**. Primary key/grain: **indicator**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| indicator | Text | 0 | Unique quality or recorded validation indicator; fixed-window/context scope. |
| value | Whole number (64-bit) | 0 | Count for quality rows; 1 means passed for recorded validation rows. Read definition. |
| denominator | Whole number (64-bit) | 0 | Relevant event/session population, or 1 for validation; not additive across indicators. |
| status | Text | 0 | pass, caution, warning or information; not a live cloud/Power BI status. |
| definition | Text | 0 | Human-readable indicator definition; use with value and denominator. |
| scope | Text | 0 | Explicit fixed-window or recorded-source-validation scope. |

## data_coverage.csv → DataCoverage

Rows: **9**. Primary key/grain: **date**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| date | Date | 0 | Dimension or coverage exported calendar date. |
| extracted_events | Whole number (64-bit) | 0 | Source-export event rows per date including adjacent context shards. |
| is_analysis_date | True/False | 0 | True for Jan 1–7; false for the two context dates. |

## window_kpis.csv → AuditWindowKpis

Rows: **1**. Primary key/grain: **dataset_id**. Role: disconnected fixed-window/context audit; no interactive relationships.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| dataset_id | Text | 0 | Fixed identifier ga4_20210101_07_real; package is not synthetic. |
| source_kind | Text | 0 | REAL_GA4_PUBLIC_SAMPLE; recorded provenance validated before export. |
| analysis_start | Date | 0 | Inclusive first requested exported analysis date. |
| analysis_end | Date | 0 | Inclusive final requested exported analysis date. |
| event_count | Whole number (64-bit) | 0 | Calendar-window event rows, with duplicates retained. |
| unique_users | Whole number (64-bit) | 0 | Distinct non-null pseudonyms in full calendar window; not sum of daily users. |
| window_active_sessions | Whole number (64-bit) | 0 | Distinct eligible composite sessions active at least once in the window. |
| entry_cohort_sessions | Whole number (64-bit) | 0 | Sessions with observed entry date in the row/window; additive across entry dates. |
| product_view_sessions | Whole number (64-bit) | 0 | Full-window observed-entry cohort sessions with ordered view_item flag. |
| ordered_purchase_sessions | Whole number (64-bit) | 0 | Full-window cohort sessions completing all four ordered stages. |
| product_view_to_purchase_rate | Decimal number (fraction) | 0 | ordered_purchase_sessions / product_view_sessions, not all sessions. |
| potentially_incomplete_cohort_sessions | Whole number (64-bit) | 0 | Included cohort sessions touching first/last context dates. |

## cohort_sessions.csv → CohortSessions

Rows: **26,328**. Primary key/grain: **session_key**. Role: fact/presence table; dimension filters only, never join to another fact.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| device_category | Text | 0 | Normalized device from earliest session event; lexicographic device on timestamp ties. |
| view_item | Whole number (64-bit) | 0 | Binary established ordered product-view reach flag for this session. |
| add_to_cart | Whole number (64-bit) | 0 | Binary established ordered cart reach flag after strictly earlier view. |
| begin_checkout | Whole number (64-bit) | 0 | Binary established ordered checkout reach flag after strictly earlier cart. |
| purchase | Whole number (64-bit) | 0 | Binary established ordered purchase reach flag after strictly earlier checkout. |
| entry_date | Date | 0 | Exported date at earliest observed cohort timestamp across context; minimum date on ties. |
| first_date | Date | 0 | Minimum exported event date observed for this composite session in context. |
| last_date | Date | 0 | Maximum exported event date observed for this composite session in context. |
| observed_dates | Whole number (64-bit) | 0 | Number of distinct exported dates observed for the session in context. |
| left_context_edge | True/False | 0 | Session touches first extracted context date; completeness uncertain. |
| right_context_edge | True/False | 0 | Session touches last extracted context date; completeness uncertain. |
| potentially_incomplete | True/False | 0 | Either context edge flag; retained in primary metrics. |
| crosses_calendar_date | True/False | 0 | More than one exported calendar date observed for one session. |
| user_key | Whole number (64-bit) | 0 | Package-local positive integer surrogate for a source pseudonym; no identity mapping exported. |
| session_key | Whole number (64-bit) | 0 | Package-local positive integer surrogate for original user+session tuple; not a source ID. |

## user_activity.csv → UserActivity

Rows: **24,157**. Primary key/grain: **activity_date, user_key**. Role: fact/presence table; dimension filters only, never join to another fact.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| activity_date | Date | 0 | Exported calendar date of observed activity; not inferred from UTC timestamp. |
| user_key | Whole number (64-bit) | 0 | Package-local positive integer surrogate for a source pseudonym; no identity mapping exported. |

## session_activity.csv → SessionActivity

Rows: **26,374**. Primary key/grain: **activity_date, session_key**. Role: fact/presence table; dimension filters only, never join to another fact.

| Field | Power BI type | Blank rows | Definition / aggregation rule |
|---|---|---:|---|
| activity_date | Date | 0 | Exported calendar date of observed activity; not inferred from UTC timestamp. |
| session_key | Whole number (64-bit) | 0 | Package-local positive integer surrogate for original user+session tuple; not a source ID. |

## Aggregation and join rules

Hide raw numeric columns and use the documented measures. Counts can be added only across disjoint grains. Users and active sessions are distinct across dates via presence tables. Product-view denominators repeat across stage rows; event denominators repeat across source/medium rows. Never sum those repeated values across stages/fields. Ratios are numerator/denominator with blanks for zero denominators. Unique stage users are nonadditive across dates/devices/stages. Static audit tables have no relationships and their values must not be displayed as if slicer-responsive. Only DimDate → dated facts and DimDevice → CohortSessions single-direction relationships are permitted; no fact-to-fact joins.
