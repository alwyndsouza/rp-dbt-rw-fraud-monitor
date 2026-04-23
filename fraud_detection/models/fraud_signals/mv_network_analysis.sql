{{ config(materialized='materialized_view') }}

-- STRETCH: Network Analysis — shared device or IP across multiple customers
-- Detects synthetic identity rings and mule account networks.
SELECT
    device_id,
    window_start,
    window_end,
    COUNT(DISTINCT customer_id) AS customer_count,
    COUNT(DISTINCT customer_id) >= 2 AS is_shared_device_ring
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '60' MINUTE)
GROUP BY
    device_id,
    window_start,
    window_end
HAVING COUNT(DISTINCT customer_id) >= 2
