{{ config(materialized='materialized_view') }}

-- SIGNAL 4: Card-Not-Present Spike — 8+ CNP transactions in a 5-minute window
SELECT
    card_last4,
    account_id,
    window_start,
    window_end,
    COUNT(*) AS cnp_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 8 AS is_cnp_spike
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '5' MINUTE)
WHERE is_cnp = TRUE
GROUP BY
    card_last4,
    account_id,
    window_start,
    window_end
HAVING COUNT(*) >= 8
