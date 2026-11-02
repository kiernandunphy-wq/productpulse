-- Caller supplies ordered_sessions. ALL aggregates across devices; DEVICE is mutually exclusive per session.
WITH stage_counts AS (
 SELECT 'ALL' AS scope, CAST(NULL AS STRING) AS device_category,
 COALESCE(SUM(view_item),0) AS n1,COALESCE(SUM(add_to_cart),0) AS n2,
 COALESCE(SUM(begin_checkout),0) AS n3,COALESCE(SUM(purchase),0) AS n4
 FROM ordered_sessions
 UNION ALL
 SELECT 'DEVICE',device_category,SUM(view_item),SUM(add_to_cart),SUM(begin_checkout),SUM(purchase)
 FROM ordered_sessions GROUP BY device_category
), stages AS (
 SELECT scope,device_category,1 AS stage_order,'view_item' AS stage,COALESCE(n1,0) AS sessions,n1 AS entry,NULL AS previous FROM stage_counts
 UNION ALL SELECT scope,device_category,2,'add_to_cart',COALESCE(n2,0),n1,n1 FROM stage_counts
 UNION ALL SELECT scope,device_category,3,'begin_checkout',COALESCE(n3,0),n1,n2 FROM stage_counts
 UNION ALL SELECT scope,device_category,4,'purchase',COALESCE(n4,0),n1,n3 FROM stage_counts
)
SELECT scope,device_category,stage_order,stage,sessions,
 1.0*sessions/NULLIF(entry,0) AS conversion_from_entry,
 1.0*sessions/NULLIF(previous,0) AS conversion_from_previous,
 previous-sessions AS abandoned_sessions,
 1.0-sessions*1.0/NULLIF(previous,0) AS abandonment_rate
FROM stages
