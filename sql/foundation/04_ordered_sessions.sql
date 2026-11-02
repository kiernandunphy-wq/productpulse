-- Portable core: caller supplies a flat CTE/view named events using the extract contract.
-- Strictly ordered, session-based; no page_view prerequisite; never cross sessions.
WITH eligible AS (
 SELECT * FROM events WHERE user_pseudo_id IS NOT NULL AND ga_session_id IS NOT NULL
), entries AS (
 SELECT user_pseudo_id, ga_session_id, MIN(event_timestamp) AS entry_time,
 MIN(CASE WHEN event_name='view_item' THEN event_timestamp END) AS t1
 FROM eligible GROUP BY user_pseudo_id,ga_session_id
), devices AS (
 SELECT a.user_pseudo_id,a.ga_session_id,
 MIN(COALESCE(NULLIF(NULLIF(NULLIF(TRIM(e.device_category),''),'<Other>'),'(not set)'),'Unknown')) AS device_category
 FROM entries a JOIN eligible e ON a.user_pseudo_id=e.user_pseudo_id
 AND a.ga_session_id=e.ga_session_id AND a.entry_time=e.event_timestamp
 GROUP BY a.user_pseudo_id,a.ga_session_id
), carts AS (
 SELECT a.user_pseudo_id,a.ga_session_id,a.t1,
 MIN(CASE WHEN e.event_name='add_to_cart' AND e.event_timestamp>a.t1 THEN e.event_timestamp END) AS t2
 FROM entries a JOIN eligible e ON a.user_pseudo_id=e.user_pseudo_id AND a.ga_session_id=e.ga_session_id
 GROUP BY a.user_pseudo_id,a.ga_session_id,a.t1
), checkouts AS (
 SELECT a.user_pseudo_id,a.ga_session_id,a.t1,a.t2,
 MIN(CASE WHEN e.event_name='begin_checkout' AND e.event_timestamp>a.t2 THEN e.event_timestamp END) AS t3
 FROM carts a JOIN eligible e ON a.user_pseudo_id=e.user_pseudo_id AND a.ga_session_id=e.ga_session_id
 GROUP BY a.user_pseudo_id,a.ga_session_id,a.t1,a.t2
), purchases AS (
 SELECT a.user_pseudo_id,a.ga_session_id,a.t1,a.t2,a.t3,
 MIN(CASE WHEN e.event_name='purchase' AND e.event_timestamp>a.t3 THEN e.event_timestamp END) AS t4
 FROM checkouts a JOIN eligible e ON a.user_pseudo_id=e.user_pseudo_id AND a.ga_session_id=e.ga_session_id
 GROUP BY a.user_pseudo_id,a.ga_session_id,a.t1,a.t2,a.t3
)
SELECT a.user_pseudo_id,a.ga_session_id,d.device_category,
 CASE WHEN t1 IS NOT NULL THEN 1 ELSE 0 END AS view_item,
 CASE WHEN t2 IS NOT NULL THEN 1 ELSE 0 END AS add_to_cart,
 CASE WHEN t3 IS NOT NULL THEN 1 ELSE 0 END AS begin_checkout,
 CASE WHEN t4 IS NOT NULL THEN 1 ELSE 0 END AS purchase
FROM purchases a JOIN devices d ON a.user_pseudo_id=d.user_pseudo_id AND a.ga_session_id=d.ga_session_id
