-- =============================================================================
-- 03_fraud_signals.sql — Real-Time Fraud Signal Detection
-- Each materialized view detects one fraud pattern using RisingWave streaming.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- SIGNAL 1: Velocity Fraud — 5+ transactions per account in rolling 60s window
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_velocity_alerts AS
SELECT
    account_id,
    card_last4,
    window_start,
    window_end,
    COUNT(*) AS txn_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 5 AS is_velocity_breach
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '60' SECOND)
GROUP BY
    account_id,
    card_last4,
    window_start,
    window_end
HAVING COUNT(*) >= 5;

-- ---------------------------------------------------------------------------
-- SIGNAL 2: Geographic Impossibility — consecutive txns > 1000km in < 2 hours
-- Uses LAG() to compare current vs previous transaction location per customer.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_geo_impossible_trips AS
WITH ordered_txns AS (
    SELECT
        customer_id,
        transaction_id,
        country_code,
        latitude,
        longitude,
        occurred_at,
        LAG(transaction_id) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_txn_id,
        LAG(country_code) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_country,
        LAG(latitude) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_lat,
        LAG(longitude) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_lon,
        LAG(occurred_at) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_occurred_at
    FROM stg_transactions
),

with_distance AS (
    SELECT
        customer_id,
        transaction_id AS txn2_id,
        country_code AS txn2_country,
        latitude AS txn2_lat,
        longitude AS txn2_lon,
        occurred_at AS txn2_time,
        prev_txn_id AS txn1_id,
        prev_country AS txn1_country,
        prev_lat AS txn1_lat,
        prev_lon AS txn1_lon,
        prev_occurred_at AS txn1_time,
        -- Haversine approximation: 1 degree lat ≈ 111km
        SQRT(
            POWER((latitude - prev_lat) * 111.0, 2)
            + POWER((longitude - prev_lon) * 111.0 * ABS(COS(RADIANS((latitude + prev_lat) / 2))), 2)
        ) AS approx_distance_km,
        EXTRACT(EPOCH FROM (occurred_at - prev_occurred_at)) / 60.0 AS time_diff_minutes
    FROM ordered_txns
    WHERE
        prev_txn_id IS NOT NULL
        AND prev_lat IS NOT NULL
)

SELECT
    customer_id,
    txn1_id,
    txn1_country,
    txn1_lat,
    txn1_lon,
    txn1_time,
    txn2_id,
    txn2_country,
    txn2_lat,
    txn2_lon,
    txn2_time,
    ROUND(approx_distance_km::NUMERIC, 2) AS approx_distance_km,
    ROUND(time_diff_minutes::NUMERIC, 2) AS time_diff_minutes,
    (approx_distance_km > 1000 AND time_diff_minutes < 120 AND time_diff_minutes > 0) AS is_impossible
FROM with_distance
WHERE approx_distance_km > 500;

-- ---------------------------------------------------------------------------
-- SIGNAL 3: Device Anomaly — new device + high-value transaction (> $500)
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_known_customer_devices AS
SELECT
    customer_id,
    device_id,
    MIN(occurred_at) AS first_seen_at,
    MAX(occurred_at) AS last_seen_at
FROM stg_transactions
GROUP BY customer_id, device_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_device_anomalies AS
WITH recent_high_value AS (
    SELECT
        t.customer_id,
        t.transaction_id,
        t.device_id,
        t.amount,
        t.occurred_at
    FROM stg_transactions AS t
    WHERE
        t.amount > 500
        AND t.channel = 'card_not_present'
        AND t.occurred_at >= NOW() - INTERVAL '10 minutes'
),

historical_known_devices AS (
    SELECT DISTINCT
        customer_id,
        device_id
    FROM stg_transactions
    WHERE
        occurred_at >= NOW() - INTERVAL '30 days'
        AND occurred_at < NOW() - INTERVAL '24 hours'
)

SELECT
    t.customer_id,
    t.transaction_id,
    t.device_id,
    t.amount,
    t.occurred_at,
    TRUE AS is_new_device_candidate,
    TRUE AS is_high_value,
    TRUE AS combined_risk_flag
FROM recent_high_value AS t
LEFT JOIN
    historical_known_devices AS d
    ON
        t.customer_id = d.customer_id
        AND t.device_id = d.device_id
WHERE d.device_id IS NULL;

-- ---------------------------------------------------------------------------
-- SIGNAL 4: Card-Not-Present Spike — 8+ CNP transactions in a 5-minute window
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_cnp_spike AS
SELECT
    card_last4,
    account_id,
    window_start,
    window_end,
    COUNT(*) AS cnp_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 8 AS is_cnp_spike
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '5' MINUTE)
WHERE is_cnp = TRUE
GROUP BY
    card_last4,
    account_id,
    window_start,
    window_end
HAVING COUNT(*) >= 8;

-- ---------------------------------------------------------------------------
-- SIGNAL 5: Login Failure Storm — 3+ failed logins in 60s (brute force)
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_login_failure_storm AS
SELECT
    customer_id,
    window_start,
    window_end,
    COUNT(*) AS failure_count,
    COUNT(DISTINCT ip_address) AS distinct_ips,
    COUNT(DISTINCT device_id) AS distinct_devices,
    MIN(occurred_at) AS first_failure_at,
    MAX(occurred_at) AS last_failure_at,
    COUNT(*) >= 3 AS is_brute_force
FROM TUMBLE(stg_login_events, occurred_at, INTERVAL '60' SECOND)
WHERE success = FALSE
GROUP BY
    customer_id,
    window_start,
    window_end
HAVING COUNT(*) >= 3;

-- ---------------------------------------------------------------------------
-- SIGNAL 6: Structuring / Smurfing — 2+ transactions $9,000-$9,999 in 60 min
-- Targets AUSTRAC AUD $10,000 reporting threshold.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_structuring_detection AS
SELECT
    account_id,
    customer_id,
    window_start,
    window_end,
    COUNT(*) AS qualifying_txn_count,
    SUM(amount) AS total_amount,
    COUNT(*) >= 2 AS is_structuring_pattern
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '60' MINUTE)
WHERE amount BETWEEN 9000 AND 9999
GROUP BY
    account_id,
    customer_id,
    window_start,
    window_end
HAVING COUNT(*) >= 2;

-- ---------------------------------------------------------------------------
-- SIGNAL 7: Compound Fraud — 2+ distinct alert types on one customer in 5 min
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_correlated_alert_burst AS
SELECT
    customer_id,
    window_start,
    window_end,
    COUNT(DISTINCT alert_type) AS alert_type_count,
    MAX(confidence_score) AS max_confidence_score,
    COUNT(DISTINCT alert_type) >= 2 AS is_compound_fraud
FROM TUMBLE(stg_alert_events, occurred_at, INTERVAL '5' MINUTE)
GROUP BY
    customer_id,
    window_start,
    window_end
HAVING COUNT(DISTINCT alert_type) >= 2;

-- ---------------------------------------------------------------------------
-- STRETCH: Network Analysis — shared device or IP across multiple customers
-- Detects synthetic identity rings and mule account networks.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_network_analysis AS
SELECT
    device_id,
    window_start,
    window_end,
    COUNT(DISTINCT customer_id) AS customer_count,
    COUNT(DISTINCT customer_id) >= 3 AS is_shared_device_ring
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '60' MINUTE)
GROUP BY
    device_id,
    window_start,
    window_end
HAVING COUNT(DISTINCT customer_id) >= 2;
