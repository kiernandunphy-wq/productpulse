# Data dictionary

For the current checkout-inclusive workflow, see [foundation definitions and outputs](foundation.md#definitions-and-outputs). The tables below describe the preserved legacy four-stage workflow; its `purchasers` column counts sessions and is not the new distinct-user KPI.

| Field / table | Grain and meaning |
|---|---|
| event_date | Required YYYYMMDD source property date; converted to datetime |
| event_timestamp | Required positive integer UTC microseconds; ordering only |
| event_name | Required event type; all names retained |
| user_pseudo_id | Nullable string browser/device pseudonym, not a person |
| ga_session_id | Nullable nonnegative integer extracted from event_params; only unique with user |
| source, medium | First-user acquisition dimensions, Unknown if missing/placeholder |
| device_category | Recorded event device; first event value used for session segmentation |
| sessions.csv | One (user_pseudo_id, ga_session_id); session_date is earliest timestamp event's source date; events count, ordered stage flags, any_purchase flag |
| funnel.csv | One ordered stage; sessions, stage_order, rate_from_entry, rate_from_previous |
| daily.csv | One session entry date; sessions, purchasers, ordered_purchases, purchase_session_rate |
| traffic.csv | One first-event source/medium combination, same measures as daily |
| segments.csv | One first-event device category, same measures as daily |
| retention.csv | One observed-first-month cohort/activity month; cohort_users, active_users, month_index, retention_rate |
| event_counts.csv | Event-name counts including rows excluded from session metrics |
| descriptive.csv | Session event-count distribution: count, mean, SD, min, quartiles, max |
| manifest.json | Provenance label/hash, quality counts, date bounds and funnel policy |
| experiment/results.json | Separate simulation-only statistical outputs |

Ordered conversion = ordered purchase sessions / page-view entry sessions. Each next event must occur strictly after the previous qualifying event. Equal timestamps cannot establish order. Sessions without page_view are excluded from the funnel entry but retained in session counts. Null zero-denominator rates are blank, never zero.

Purchase-session rate = sessions containing any purchase / all eligible sessions. Purchasers here means purchase sessions, not distinct people, orders or transaction IDs. A user can appear in multiple sessions. No deduplication of transactions is attempted.

Retention rate = distinct cohort pseudonyms active in month / original cohort pseudonyms. Month zero is 100% by definition; cohorts are left-censored by the extract start, and late activity is right-censored. Future months are omitted. Zero populated cells require confirmation that the source period has full coverage. Local timestamps and event_date mismatches require investigation rather than automatic rewriting.
