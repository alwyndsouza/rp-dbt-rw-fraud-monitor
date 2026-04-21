-- =============================================================================
-- 05_case_management.sql — Fraud Investigation Case Management
-- Surfaces accounts requiring human review with recommended actions.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Active fraud cases — accounts in HIGH or CRITICAL risk state
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_open_fraud_cases AS
SELECT
    r.account_id,
    r.customer_id,
    r.risk_score,
    r.risk_tier,
    r.contributing_signals,
    COALESCE(k.risk_tier, 'unknown') AS kyc_risk_tier,
    CASE
        WHEN
            r.risk_score > 0.9
            OR COALESCE(k.risk_tier, '') IN ('pep', 'sanctioned')
            THEN 'escalate'
        WHEN
            r.risk_score > 0.75
            AND 'structuring' = ANY(r.contributing_signals)
            THEN 'freeze_account'
        WHEN
            r.risk_score > 0.6
            AND (
                'velocity' = ANY(r.contributing_signals)
                OR 'cnp_spike' = ANY(r.contributing_signals)
            )
            THEN 'block_card'
        ELSE 'monitor'
    END AS recommended_action
FROM mv_account_risk_score_realtime AS r
LEFT JOIN mv_latest_kyc AS k ON r.customer_id = k.customer_id
WHERE r.risk_tier IN ('high', 'critical');

-- ---------------------------------------------------------------------------
-- Cases resolved today — risk score normalised below 0.3
-- Used for analyst performance metrics and case closure reporting.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resolved_cases_today AS
SELECT
    account_id,
    customer_id,
    risk_score AS current_risk_score
FROM mv_account_risk_score_realtime
WHERE risk_score < 0.3;

-- ---------------------------------------------------------------------------
-- High-severity alert summary — last 30 minutes
-- Quick-look table for SOC analysts monitoring the operations centre.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_high_alerts AS
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
FROM stg_alert_events AS a
LEFT JOIN mv_latest_kyc AS k ON a.customer_id = k.customer_id
WHERE
    a.severity IN ('high', 'critical')
    AND a.occurred_at >= NOW() - INTERVAL '30 minutes';
