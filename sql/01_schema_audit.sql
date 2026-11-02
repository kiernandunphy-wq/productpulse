-- GoogleSQL. Run before extraction. Confirm nested field paths rather than assuming modern GA4 fields exist.
SELECT table_name, field_path, data_type
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
WHERE table_name = 'events_20201101'
ORDER BY field_path;

SELECT event_name, COUNT(*) AS events,
 COUNTIF(user_pseudo_id IS NULL) AS missing_user,
 COUNTIF((SELECT COUNT(*) FROM UNNEST(event_params) WHERE key='ga_session_id')=0) AS missing_session,
 COUNTIF((SELECT COUNT(*) FROM UNNEST(event_params) WHERE key='ga_session_id')>1) AS duplicate_session_keys
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
GROUP BY event_name;
