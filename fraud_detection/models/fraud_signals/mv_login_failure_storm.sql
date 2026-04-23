{{ config(materialized='materialized_view') }}

-- SIGNAL 5: Login Failure Storm — 3+ failed logins in 60s (brute force)
SELECT
    customer_id,
    window_start,
    window_end,
    COUNT(*) AS failure_count,
    COUNT(DISTINCT ip_address) AS distinct_ips,
    COUNT(DISTINCT device_id) AS distinct_devices,
    MIN(occurred_at) AS first_failure_at,
    MAX(occurred_at) AS last_failure_at,
    COUNT(*) >= 3 AS is_brute_force
FROM TUMBLE({{ ref('stg_login_events') }}, occurred_at, INTERVAL '60' SECOND)
WHERE success = FALSE
GROUP BY
    customer_id,
    window_start,
    window_end
HAVING COUNT(*) >= 3
