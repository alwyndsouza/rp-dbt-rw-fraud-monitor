{{ config(materialized='materialized_view') }}

-- Account-level rolling risk score (0.0 – 1.0)
-- Combines signals from fraud signal views with additive weights, capped at 1.
WITH recent_velocity AS (
    SELECT
        account_id,
        MAX(CASE WHEN is_velocity_breach THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_velocity_alerts') }}
    WHERE window_end >= NOW() - INTERVAL '10 minutes'
    GROUP BY account_id
),

recent_geo AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN g.is_impossible THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_geo_impossible_trips') }} AS g
    INNER JOIN {{ ref('stg_transactions') }} AS t ON g.txn2_id = t.transaction_id
    WHERE g.txn2_time >= NOW() - INTERVAL '30 minutes'
    GROUP BY t.account_id
),

recent_device AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN d.combined_risk_flag THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_device_anomalies') }} AS d
    INNER JOIN {{ ref('stg_transactions') }} AS t ON d.transaction_id = t.transaction_id
    WHERE d.occurred_at >= NOW() - INTERVAL '10 minutes'
    GROUP BY t.account_id
),

recent_cnp AS (
    SELECT
        account_id,
        MAX(CASE WHEN is_cnp_spike THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_cnp_spike') }}
    WHERE window_end >= NOW() - INTERVAL '5 minutes'
    GROUP BY account_id
),

recent_brute AS (
    SELECT
        l.customer_id,
        t.account_id,
        MAX(CASE WHEN l.is_brute_force THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_login_failure_storm') }} AS l
    INNER JOIN {{ ref('stg_transactions') }} AS t ON l.customer_id = t.customer_id
    WHERE l.window_end >= NOW() - INTERVAL '5 minutes'
    GROUP BY l.customer_id, t.account_id
),

recent_struct AS (
    SELECT
        account_id,
        customer_id,
        MAX(CASE WHEN is_structuring_pattern THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_structuring_detection') }}
    WHERE window_end >= NOW() - INTERVAL '60 minutes'
    GROUP BY account_id, customer_id
),

recent_compound AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN c.is_compound_fraud THEN 1 ELSE 0 END) AS flag
    FROM {{ ref('mv_correlated_alert_burst') }} AS c
    INNER JOIN {{ ref('stg_transactions') }} AS t ON c.customer_id = t.customer_id
    WHERE c.window_end >= NOW() - INTERVAL '10 minutes'
    GROUP BY t.account_id
),

all_accounts AS (
    SELECT DISTINCT
        account_id,
        customer_id
    FROM {{ ref('stg_transactions') }}
    WHERE occurred_at >= NOW() - INTERVAL '60 minutes'
),

scored_accounts AS (
    SELECT
        a.account_id,
        a.customer_id,
        (
            0.1
            + COALESCE(rv.flag, 0) * 0.25
            + COALESCE(rg.flag, 0) * 0.30
            + COALESCE(rd.flag, 0) * 0.20
            + COALESCE(rc.flag, 0) * 0.15
            + COALESCE(rb.flag, 0) * 0.35
            + COALESCE(rs.flag, 0) * 0.40
            + COALESCE(rcomp.flag, 0) * 0.20
        ) AS risk_score_raw,
        ARRAY_REMOVE(ARRAY[
            CASE WHEN COALESCE(rv.flag, 0) = 1 THEN 'velocity' END,
            CASE WHEN COALESCE(rg.flag, 0) = 1 THEN 'geo_impossible' END,
            CASE WHEN COALESCE(rd.flag, 0) = 1 THEN 'device_anomaly' END,
            CASE WHEN COALESCE(rc.flag, 0) = 1 THEN 'cnp_spike' END,
            CASE WHEN COALESCE(rb.flag, 0) = 1 THEN 'brute_force' END,
            CASE WHEN COALESCE(rs.flag, 0) = 1 THEN 'structuring' END,
            CASE WHEN COALESCE(rcomp.flag, 0) = 1 THEN 'compound_fraud' END
        ], NULL) AS contributing_signals
    FROM all_accounts AS a
    LEFT JOIN recent_velocity AS rv ON a.account_id = rv.account_id
    LEFT JOIN recent_geo AS rg ON a.account_id = rg.account_id
    LEFT JOIN recent_device AS rd ON a.account_id = rd.account_id
    LEFT JOIN recent_cnp AS rc ON a.account_id = rc.account_id
    LEFT JOIN recent_brute AS rb
        ON
            a.account_id = rb.account_id
            AND a.customer_id = rb.customer_id
    LEFT JOIN recent_struct AS rs ON a.account_id = rs.account_id
    LEFT JOIN recent_compound AS rcomp ON a.account_id = rcomp.account_id
),

capped_scores AS (
    SELECT
        account_id,
        customer_id,
        LEAST(1.0, risk_score_raw)::DOUBLE PRECISION AS risk_score,
        contributing_signals
    FROM scored_accounts
)

SELECT
    c.account_id,
    c.customer_id,
    c.risk_score,
    c.contributing_signals,
    CASE
        WHEN c.risk_score > 0.8 THEN 'critical'
        WHEN c.risk_score > 0.5 THEN 'high'
        WHEN c.risk_score > 0.3 THEN 'medium'
        ELSE 'low'
    END AS risk_tier
FROM capped_scores AS c
