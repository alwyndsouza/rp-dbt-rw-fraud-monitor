{{ config(materialized='materialized_view') }}

-- SIGNAL 6: Structuring / Smurfing — 2+ transactions $9,000-$9,999 in 60 min
-- Targets AUSTRAC AUD $10,000 reporting threshold.
SELECT
    account_id,
    customer_id,
    window_start,
    window_end,
    COUNT(*) AS qualifying_txn_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 2 AS is_structuring_pattern
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '60' MINUTE)
WHERE amount BETWEEN 9000 AND 9999
GROUP BY
    account_id,
    customer_id,
    window_start,
    window_end
HAVING COUNT(*) >= 2
