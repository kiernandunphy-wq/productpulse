-- GoogleSQL. User-acquisition source, not session-attributed campaign performance.
WITH flat AS (
 SELECT event_date, event_timestamp, event_name, user_pseudo_id,
  (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_id') AS sid,
  traffic_source.source AS source, traffic_source.medium AS medium,
  device.category AS device_category
 FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
 WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107'
), sessions AS (
 SELECT user_pseudo_id, sid,
  ARRAY_AGG(STRUCT(event_timestamp,source,medium,device_category) ORDER BY event_timestamp LIMIT 1)[OFFSET(0)] AS first_event,
  COUNTIF(event_name='page_view') AS page_views,
  COUNTIF(event_name='view_item') AS product_views,
  COUNTIF(event_name='add_to_cart') AS cart_additions,
  MAX(IF(event_name='purchase',1,0)) AS any_purchase
 FROM flat WHERE user_pseudo_id IS NOT NULL AND sid IS NOT NULL GROUP BY 1,2
)
SELECT first_event.source AS source, first_event.medium AS medium,
 first_event.device_category AS device_category,
 COUNT(*) AS sessions, SUM(page_views) AS page_views, SUM(product_views) AS product_views,
 SUM(cart_additions) AS cart_additions, SUM(any_purchase) AS purchase_sessions,
 SAFE_DIVIDE(SUM(any_purchase),COUNT(*)) AS purchase_session_rate
FROM sessions GROUP BY 1,2,3;
