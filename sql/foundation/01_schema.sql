-- GoogleSQL, one concrete shard. Change the date consistently in all foundation queries.
SELECT field_path, data_type
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
WHERE table_name = 'events_20210101'
ORDER BY field_path;
