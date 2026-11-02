-- GoogleSQL. January 1–7, 2021. Review estimated bytes before running.
-- User counts overlap across events: do not sum them.
SELECT event_name, COUNT(*) AS event_count,
  COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107'
GROUP BY event_name
ORDER BY event_count DESC;

-- Reconcile daily counts against the event-level CSV export.
SELECT event_date, COUNT(*) AS event_count,
  COUNTIF(user_pseudo_id IS NULL) AS missing_user_events
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107'
GROUP BY event_date
ORDER BY event_date;
