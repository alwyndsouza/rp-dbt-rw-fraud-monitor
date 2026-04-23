{{ config(materialized='materialized_view') }}

-- 24-hour rolling fraud trend — hourly buckets
SELECT
    window_start AS hour_bucket,
    COUNT(*) AS total_txns,
    COUNT(*) FILTER (WHERE is_high_risk_mcc) AS fraud_flags,
    ROUND(
        CASE
            WHEN COUNT(*) > 0
                THEN
                    COUNT(*) FILTER (WHERE is_high_risk_mcc)::DOUBLE PRECISION
                    / COUNT(*) * 100
            ELSE 0
        END::NUMERIC, 2
    ) AS fraud_rate_pct,
    ROUND(SUM(amount)::NUMERIC, 2) AS total_value
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '1' HOUR)
GROUP BY window_start
