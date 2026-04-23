{{ config(materialized='materialized_view') }}

-- SIGNAL 1: Velocity Fraud — 5+ transactions per account in rolling 60s window
SELECT
    account_id,
    card_last4,
    window_start,
    window_end,
    COUNT(*) AS txn_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 5 AS is_velocity_breach
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '60' SECOND)
GROUP BY
    account_id,
    card_last4,
    window_start,
    window_end
HAVING COUNT(*) >= 5
