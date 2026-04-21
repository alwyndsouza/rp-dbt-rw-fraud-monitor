-- =============================================================================
-- 04_risk_aggregations.sql — Risk Scoring & Operational KPI Aggregations
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Account-level rolling risk score (0.0 – 1.0)
-- Combines signals from fraud signal views with additive weights, capped at 1.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_account_risk_score_realtime AS
WITH recent_velocity AS (
    SELECT
        account_id,
        MAX(CASE WHEN is_velocity_breach THEN 1 ELSE 0 END) AS flag
    FROM mv_velocity_alerts
    WHERE window_end >= NOW() - INTERVAL '10 minutes'
    GROUP BY account_id
),

recent_geo AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN g.is_impossible THEN 1 ELSE 0 END) AS flag
    FROM mv_geo_impossible_trips AS g
    INNER JOIN stg_transactions AS t ON g.txn2_id = t.transaction_id
    WHERE g.txn2_time >= NOW() - INTERVAL '30 minutes'
    GROUP BY t.account_id
),

recent_device AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN d.combined_risk_flag THEN 1 ELSE 0 END) AS flag
    FROM mv_device_anomalies AS d
    INNER JOIN stg_transactions AS t ON d.transaction_id = t.transaction_id
    WHERE d.occurred_at >= NOW() - INTERVAL '10 minutes'
    GROUP BY t.account_id
),

recent_cnp AS (
    SELECT
        account_id,
        MAX(CASE WHEN is_cnp_spike THEN 1 ELSE 0 END) AS flag
    FROM mv_cnp_spike
    WHERE window_end >= NOW() - INTERVAL '5 minutes'
    GROUP BY account_id
),

recent_brute AS (
    SELECT
        l.customer_id,
        t.account_id,
        MAX(CASE WHEN l.is_brute_force THEN 1 ELSE 0 END) AS flag
    FROM mv_login_failure_storm AS l
    INNER JOIN stg_transactions AS t ON l.customer_id = t.customer_id
    WHERE l.window_end >= NOW() - INTERVAL '5 minutes'
    GROUP BY l.customer_id, t.account_id
),

recent_struct AS (
    SELECT
        account_id,
        customer_id,
        MAX(CASE WHEN is_structuring_pattern THEN 1 ELSE 0 END) AS flag
    FROM mv_structuring_detection
    WHERE window_end >= NOW() - INTERVAL '60 minutes'
    GROUP BY account_id, customer_id
),

recent_compound AS (
    SELECT
        t.account_id,
        MAX(CASE WHEN c.is_compound_fraud THEN 1 ELSE 0 END) AS flag
    FROM mv_correlated_alert_burst AS c
    INNER JOIN stg_transactions AS t ON c.customer_id = t.customer_id
    WHERE c.window_end >= NOW() - INTERVAL '10 minutes'
    GROUP BY t.account_id
),

all_accounts AS (
    SELECT DISTINCT
        account_id,
        customer_id
    FROM stg_transactions
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
FROM capped_scores AS c;

-- ---------------------------------------------------------------------------
-- Fraud operations KPIs — 1-minute tumbling windows
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_fraud_kpis_1min AS
WITH txn_window AS (
    SELECT
        window_start,
        window_end,
        COUNT(*) AS total_transactions,
        SUM(amount) AS total_transaction_value,
        COUNT(*) FILTER (WHERE is_high_risk_mcc) AS flagged_transactions
    FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '1' MINUTE)
    GROUP BY window_start, window_end
),

velocity_window AS (
    SELECT
        window_start,
        COUNT(*) AS velocity_breaches
    FROM mv_velocity_alerts
    WHERE is_velocity_breach
    GROUP BY window_start
),

geo_window AS (
    SELECT
        DATE_TRUNC('minute', txn2_time) AS window_start,
        COUNT(*) AS geo_anomalies
    FROM mv_geo_impossible_trips
    WHERE is_impossible
    GROUP BY DATE_TRUNC('minute', txn2_time)
),

brute_window AS (
    SELECT
        window_start,
        COUNT(*) AS brute_force_attempts
    FROM mv_login_failure_storm
    WHERE is_brute_force
    GROUP BY window_start
),

struct_window AS (
    SELECT
        window_start,
        COUNT(*) AS structuring_flags
    FROM mv_structuring_detection
    WHERE is_structuring_pattern
    GROUP BY window_start
),

alert_window AS (
    SELECT
        window_start,
        AVG(confidence_score) AS avg_alert_confidence
    FROM TUMBLE(stg_alert_events, occurred_at, INTERVAL '1' MINUTE)
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
LEFT JOIN alert_window AS aw ON tw.window_start = aw.window_start;

-- ---------------------------------------------------------------------------
-- Merchant fraud exposure — rolling 1-hour window
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_merchant_fraud_exposure AS
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
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '1' HOUR)
GROUP BY merchant_id, merchant_name, merchant_category_code, window_start
HAVING COUNT(*) >= 2;

-- ---------------------------------------------------------------------------
-- Channel risk breakdown — rolling 1-hour window
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_channel_risk_breakdown AS
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
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '1' HOUR)
GROUP BY channel, window_start;

-- ---------------------------------------------------------------------------
-- 24-hour rolling fraud trend — hourly buckets
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_fraud_trend AS
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
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '1' HOUR)
GROUP BY window_start;
