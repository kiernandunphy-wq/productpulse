-- Observed first month, not acquisition month. Expand to full range for cohort analysis.
WITH activity AS (
 SELECT DISTINCT user_pseudo_id, PARSE_DATE('%Y%m%d',event_date) AS day,
 device.category AS device_category
 FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
 WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131' AND user_pseudo_id IS NOT NULL
), cohorts AS (
 SELECT user_pseudo_id, DATE_TRUNC(MIN(day),MONTH) AS cohort_month
 FROM activity GROUP BY 1
), sizes AS (
 SELECT cohort_month, COUNT(*) AS cohort_users FROM cohorts GROUP BY 1
), counts AS (
 SELECT cohort_month, DATE_TRUNC(day,MONTH) AS activity_month,
 COUNT(DISTINCT user_pseudo_id) AS active_users
 FROM activity JOIN cohorts USING(user_pseudo_id) GROUP BY 1,2
), grid AS (
 SELECT s.*, month AS activity_month FROM sizes s,
 UNNEST(GENERATE_DATE_ARRAY(cohort_month, DATE '2021-01-01', INTERVAL 1 MONTH)) AS month
)
SELECT g.*, DATE_DIFF(activity_month,cohort_month,MONTH) AS month_index,
 COALESCE(active_users,0) AS active_users,
 SAFE_DIVIDE(COALESCE(active_users,0),cohort_users) AS retention_rate
FROM grid g LEFT JOIN counts USING(cohort_month,activity_month)
ORDER BY cohort_month,activity_month;
