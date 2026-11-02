-- GoogleSQL. Same earliest-valid-next-event policy as Python; strict > resolves ambiguous timestamp ties conservatively.
WITH events AS (
 SELECT user_pseudo_id, event_timestamp, event_name,
 (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_id') AS sid
 FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
 WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107'
), eligible AS (
 SELECT * FROM events WHERE user_pseudo_id IS NOT NULL AND sid IS NOT NULL
), entry AS (
 SELECT user_pseudo_id, sid, MIN(IF(event_name='page_view',event_timestamp,NULL)) AS t1
 FROM eligible GROUP BY 1,2
), views AS (
 SELECT a.*, MIN(IF(e.event_name='view_item' AND e.event_timestamp>a.t1,e.event_timestamp,NULL)) AS t2
 FROM entry a JOIN eligible e USING(user_pseudo_id,sid) GROUP BY 1,2,3
), carts AS (
 SELECT a.*, MIN(IF(e.event_name='add_to_cart' AND e.event_timestamp>a.t2,e.event_timestamp,NULL)) AS t3
 FROM views a JOIN eligible e USING(user_pseudo_id,sid) GROUP BY 1,2,3,4
), purchases AS (
 SELECT a.*, MIN(IF(e.event_name='purchase' AND e.event_timestamp>a.t3,e.event_timestamp,NULL)) AS t4
 FROM carts a JOIN eligible e USING(user_pseudo_id,sid) GROUP BY 1,2,3,4,5
)
SELECT COUNT(*) AS eligible_sessions, COUNT(t1) AS page_view_sessions,
 COUNT(t2) AS view_item_sessions, COUNT(t3) AS add_to_cart_sessions, COUNT(t4) AS purchase_sessions,
 SAFE_DIVIDE(COUNT(t4),COUNT(t1)) AS ordered_conversion
FROM purchases;
