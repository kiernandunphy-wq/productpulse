-- One shard; retain all events to define unique users and session entry device accurately.
-- Reject repeated ga_session_id keys before using MAX (see extractor audit).
SELECT event_date, event_timestamp, event_name, user_pseudo_id,
 (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_id') AS ga_session_id,
 traffic_source.source AS source, traffic_source.medium AS medium,
 device.category AS device_category
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_20210101`
