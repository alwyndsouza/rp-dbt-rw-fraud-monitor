{{ config(materialized='materialized_view') }}

-- SIGNAL 3 (helper): Known devices per customer — used by mv_device_anomalies
SELECT
    customer_id,
    device_id,
    MIN(occurred_at) AS first_seen_at,
    MAX(occurred_at) AS last_seen_at
FROM {{ ref('stg_transactions') }}
GROUP BY customer_id, device_id
