{{ config(materialized='materialized_view') }}

-- Channel risk breakdown — rolling 1-hour window
SELECT
    channel,
    window_start,
    COUNT(*) AS txn_count,
    COUNT(*) FILTER (WHERE is_high_risk_mcc) AS flagged_count,
    ROUND(SUM(amount)::NUMERIC, 2) AS total_value,
    ROUND(SUM(amount) FILTER (WHERE is_high_risk_mcc)::NUMERIC, 2) AS flagged_value,
    ROUND(
        CASE
            WHEN COUNT(*) > 0
                THEN
                    COUNT(*) FILTER (WHERE is_high_risk_mcc)::DOUBLE PRECISION
                    / COUNT(*) * 100
            ELSE 0
        END::NUMERIC, 2
    ) AS fraud_rate_pct,
    ROUND(AVG(amount)::NUMERIC, 2) AS avg_amount
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '1' HOUR)
GROUP BY channel, window_start
