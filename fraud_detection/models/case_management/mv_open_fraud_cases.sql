{{ config(materialized='materialized_view') }}

-- Active fraud cases — accounts in HIGH or CRITICAL risk state
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
FROM {{ ref('mv_account_risk_score_realtime') }} AS r
LEFT JOIN {{ ref('mv_latest_kyc') }} AS k ON r.customer_id = k.customer_id
WHERE r.risk_tier IN ('high', 'critical')
