-- GoogleSQL; one row per original event. Do not UNNEST items here: it would multiply event rows.
-- Match the seven-day inventory. Expand literal suffixes after checking bytes processed.
SELECT event_date, event_timestamp, event_name, user_pseudo_id,
 (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_id') AS ga_session_id,
 traffic_source.source AS source, traffic_source.medium AS medium,
 device.category AS device_category
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107';
