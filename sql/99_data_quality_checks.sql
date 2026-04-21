-- =============================================================================
-- 99_data_quality_checks.sql — Runtime data quality guardrails
-- Execute manually or via scripts/run_data_quality_checks.sh
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Freshness checks (event-time lag should remain within SLA)
-- ---------------------------------------------------------------------------
SELECT
    'transactions_freshness_seconds' AS check_name,
    EXTRACT(EPOCH FROM (NOW() - MAX(occurred_at)))::BIGINT AS check_value
FROM stg_transactions;

SELECT
    'login_events_freshness_seconds' AS check_name,
    EXTRACT(EPOCH FROM (NOW() - MAX(occurred_at)))::BIGINT AS check_value
FROM stg_login_events;

SELECT
    'alerts_freshness_seconds' AS check_name,
    EXTRACT(EPOCH FROM (NOW() - MAX(occurred_at)))::BIGINT AS check_value
FROM stg_alert_events;

-- ---------------------------------------------------------------------------
-- Duplicate checks by natural event IDs
-- ---------------------------------------------------------------------------
SELECT
    'duplicate_transactions' AS check_name,
    COUNT(*) AS check_value
FROM (
    SELECT transaction_id
    FROM stg_transactions
    GROUP BY transaction_id
    HAVING COUNT(*) > 1
) AS dup;

SELECT
    'duplicate_logins' AS check_name,
    COUNT(*) AS check_value
FROM (
    SELECT event_id
    FROM stg_login_events
    GROUP BY event_id
    HAVING COUNT(*) > 1
) AS dup;

SELECT
    'duplicate_alerts' AS check_name,
    COUNT(*) AS check_value
FROM (
    SELECT alert_id
    FROM stg_alert_events
    GROUP BY alert_id
    HAVING COUNT(*) > 1
) AS dup;

-- ---------------------------------------------------------------------------
-- Null/contract sanity checks on critical dimensions
-- ---------------------------------------------------------------------------
SELECT
    'null_transaction_keys' AS check_name,
    COUNT(*) AS check_value
FROM stg_transactions
WHERE transaction_id IS NULL OR account_id IS NULL OR customer_id IS NULL;

SELECT
    'null_login_keys' AS check_name,
    COUNT(*) AS check_value
FROM stg_login_events
WHERE event_id IS NULL OR customer_id IS NULL;
