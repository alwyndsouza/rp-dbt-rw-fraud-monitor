{{ config(materialized='materialized_view') }}

SELECT
    alert_id,
    customer_id,
    transaction_id,
    alert_type,
    severity,
    confidence_score,
    rule_id,
    occurred_at::TIMESTAMPTZ AS occurred_at,
    -- Severity as numeric weight for risk scoring
    CASE severity
        WHEN 'critical' THEN 4
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 2
        ELSE 1
    END AS severity_weight
FROM {{ ref('alert_events') }}
