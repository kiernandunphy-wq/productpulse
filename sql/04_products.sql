-- Item grain is separate from event grain. Missing IDs remain visible; quantities are not event counts.
SELECT item.item_id, item.item_name, e.event_name,
 COUNT(*) AS item_rows, SUM(item.quantity) AS quantity,
 COUNTIF(item.quantity IS NULL) AS missing_quantity_rows
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` e,
 UNNEST(e.items) AS item
WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210107'
 AND e.event_name IN ('view_item','add_to_cart','purchase')
GROUP BY 1,2,3;
