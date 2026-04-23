{{ config(materialized='materialized_view') }}

-- High-severity alert summary — last 30 minutes
-- Quick-look table for SOC analysts monitoring the operations centre.
SELECT
    a.alert_id,
    a.customer_id,
    a.transaction_id,
    a.alert_type,
    a.severity,
    a.rule_id,
    a.occurred_at,
    ROUND(a.confidence_score::NUMERIC, 4) AS confidence_score,
    COALESCE(k.risk_tier, 'unknown') AS customer_kyc_tier,
    COALESCE(k.kyc_status, 'unknown') AS kyc_status
FROM {{ ref('stg_alert_events') }} AS a
LEFT JOIN {{ ref('mv_latest_kyc') }} AS k ON a.customer_id = k.customer_id
WHERE
    a.severity IN ('high', 'critical')
    AND a.occurred_at >= NOW() - INTERVAL '30 minutes'
