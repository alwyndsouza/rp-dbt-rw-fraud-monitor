{{ config(materialized='materialized_view') }}

-- Fraud operations KPIs — 1-minute tumbling windows
WITH txn_window AS (
    SELECT
        window_start,
        window_end,
        COUNT(*) AS total_transactions,
        SUM(amount) AS total_transaction_value,
        COUNT(*) FILTER (WHERE is_high_risk_mcc) AS flagged_transactions
    FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '1' MINUTE)
    GROUP BY window_start, window_end
),

velocity_window AS (
    SELECT
        window_start,
        COUNT(*) AS velocity_breaches
    FROM {{ ref('mv_velocity_alerts') }}
    WHERE is_velocity_breach
    GROUP BY window_start
),

geo_window AS (
    SELECT
        DATE_TRUNC('minute', txn2_time) AS window_start,
        COUNT(*) AS geo_anomalies
    FROM {{ ref('mv_geo_impossible_trips') }}
    WHERE is_impossible
    GROUP BY DATE_TRUNC('minute', txn2_time)
),

brute_window AS (
    SELECT
        window_start,
        COUNT(*) AS brute_force_attempts
    FROM {{ ref('mv_login_failure_storm') }}
    WHERE is_brute_force
    GROUP BY window_start
),

struct_window AS (
    SELECT
        window_start,
        COUNT(*) AS structuring_flags
    FROM {{ ref('mv_structuring_detection') }}
    WHERE is_structuring_pattern
    GROUP BY window_start
),

alert_window AS (
    SELECT
        window_start,
        AVG(confidence_score) AS avg_alert_confidence
    FROM TUMBLE({{ ref('stg_alert_events') }}, occurred_at, INTERVAL '1' MINUTE)
    GROUP BY window_start
)

SELECT
    tw.window_start,
    tw.window_end,
    tw.total_transactions,
    tw.flagged_transactions,
    0 AS critical_risk_accounts,
    ROUND(tw.total_transaction_value::NUMERIC, 2) AS total_transaction_value,
    ROUND(
        CASE
            WHEN tw.total_transactions > 0
                THEN tw.flagged_transactions::DOUBLE PRECISION / tw.total_transactions * 100
            ELSE 0
        END::NUMERIC, 2
    ) AS fraud_rate_pct,
    COALESCE(vw.velocity_breaches, 0) AS velocity_breaches,
    COALESCE(gw.geo_anomalies, 0) AS geo_anomalies,
    COALESCE(bw.brute_force_attempts, 0) AS brute_force_attempts,
    COALESCE(sw.structuring_flags, 0) AS structuring_flags,
    ROUND(COALESCE(aw.avg_alert_confidence, 0)::NUMERIC, 4) AS avg_alert_confidence
FROM txn_window AS tw
LEFT JOIN velocity_window AS vw ON tw.window_start = vw.window_start
LEFT JOIN geo_window AS gw ON tw.window_start = gw.window_start
LEFT JOIN brute_window AS bw ON tw.window_start = bw.window_start
LEFT JOIN struct_window AS sw ON tw.window_start = sw.window_start
LEFT JOIN alert_window AS aw ON tw.window_start = aw.window_start
