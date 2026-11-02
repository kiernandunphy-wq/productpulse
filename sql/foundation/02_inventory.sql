-- Actual event names are unknown until this query has run successfully.
SELECT event_name, COUNT(*) AS event_count,
 COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_20210101`
GROUP BY event_name ORDER BY event_count DESC;
