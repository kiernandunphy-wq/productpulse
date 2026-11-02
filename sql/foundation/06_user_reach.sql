-- Caller supplies flat events. These are unordered users, not funnel completions.
SELECT event_name,COUNT(*) AS event_count,COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM events GROUP BY event_name;
