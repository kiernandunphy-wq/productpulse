-- Caller supplies normalized events; distinct pseudonyms, no ordering requirement.
SELECT COUNT(*) AS event_count,COUNT(DISTINCT user_pseudo_id) AS unique_users,
 COUNT(DISTINCT CASE WHEN event_name='view_item' THEN user_pseudo_id END) AS product_viewers,
 COUNT(DISTINCT CASE WHEN event_name='add_to_cart' THEN user_pseudo_id END) AS add_to_cart_users,
 COUNT(DISTINCT CASE WHEN event_name='begin_checkout' THEN user_pseudo_id END) AS checkout_starters,
 COUNT(DISTINCT CASE WHEN event_name='purchase' THEN user_pseudo_id END) AS purchasers
FROM events
