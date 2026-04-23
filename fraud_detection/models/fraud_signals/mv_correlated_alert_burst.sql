{{ config(materialized='materialized_view') }}

-- SIGNAL 7: Compound Fraud — 2+ distinct alert types on one customer in 5 min
SELECT
    customer_id,
    window_start,
    window_end,
    COUNT(DISTINCT alert_type) AS alert_type_count,
    MAX(confidence_score) AS max_confidence_score,
    COUNT(DISTINCT alert_type) >= 2 AS is_compound_fraud
FROM TUMBLE({{ ref('stg_alert_events') }}, occurred_at, INTERVAL '5' MINUTE)
GROUP BY
    customer_id,
    window_start,
    window_end
HAVING COUNT(DISTINCT alert_type) >= 2
