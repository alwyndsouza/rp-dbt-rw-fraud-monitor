{{ config(materialized='materialized_view') }}

-- Merchant fraud exposure — rolling 1-hour window
SELECT
    merchant_id,
    merchant_name,
    merchant_category_code,
    window_start,
    COUNT(*) AS total_txns,
    COUNT(*) FILTER (WHERE is_high_risk_mcc) AS flagged_txns,
    ROUND(
        CASE
            WHEN COUNT(*) > 0
                THEN
                    COUNT(*) FILTER (WHERE is_high_risk_mcc)::DOUBLE PRECISION
                    / COUNT(*) * 100
            ELSE 0
        END::NUMERIC, 2
    ) AS fraud_exposure_pct,
    ROUND(SUM(amount)::NUMERIC, 2) AS total_value,
    ROUND(SUM(amount) FILTER (WHERE is_high_risk_mcc)::NUMERIC, 2) AS flagged_value
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '1' HOUR)
GROUP BY merchant_id, merchant_name, merchant_category_code, window_start
HAVING COUNT(*) >= 2
