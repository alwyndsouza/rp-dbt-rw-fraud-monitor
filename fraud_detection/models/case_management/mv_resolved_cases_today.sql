{{ config(materialized='materialized_view') }}

-- Cases resolved today — risk score normalised below 0.3
-- Used for analyst performance metrics and case closure reporting.
SELECT
    account_id,
    customer_id,
    risk_score AS current_risk_score
FROM {{ ref('mv_account_risk_score_realtime') }}
WHERE risk_score < 0.3
