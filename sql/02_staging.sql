-- =============================================================================
-- 02_staging.sql — Parsed & Enriched Staging Materialized Views
-- Casts VARCHAR timestamps to TIMESTAMPTZ, adds derived indicator columns.
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS stg_transactions AS
SELECT
    transaction_id,
    account_id,
    customer_id,
    amount,
    currency,
    merchant_id,
    merchant_category_code,
    merchant_name,
    channel,
    card_last4,
    device_id,
    ip_address,
    latitude,
    longitude,
    country_code,
    occurred_at::TIMESTAMPTZ AS occurred_at,
    status,
    -- Derived fields
    EXTRACT(HOUR FROM occurred_at::TIMESTAMPTZ) AS txn_hour,
    COALESCE(EXTRACT(HOUR FROM occurred_at::TIMESTAMPTZ) BETWEEN 2 AND 4, false) AS is_odd_hours,
    (channel = 'card_not_present') AS is_cnp,
    (merchant_category_code IN ('6011', '7995', '6051')) AS is_high_risk_mcc
FROM transactions;

CREATE MATERIALIZED VIEW IF NOT EXISTS stg_login_events AS
SELECT
    event_id,
    customer_id,
    device_id,
    ip_address,
    country_code,
    latitude,
    longitude,
    user_agent,
    success,
    failure_reason,
    occurred_at::TIMESTAMPTZ AS occurred_at
FROM login_events;

CREATE MATERIALIZED VIEW IF NOT EXISTS stg_card_events AS
SELECT
    event_id,
    account_id,
    customer_id,
    card_last4,
    event_type,
    initiated_by,
    occurred_at::TIMESTAMPTZ AS occurred_at
FROM card_events;

CREATE MATERIALIZED VIEW IF NOT EXISTS stg_alert_events AS
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
FROM alert_events;

CREATE MATERIALIZED VIEW IF NOT EXISTS stg_kyc_profiles AS
SELECT
    customer_id,
    risk_tier,
    kyc_status,
    account_type,
    country_of_residence,
    updated_at::TIMESTAMPTZ AS updated_at
FROM kyc_profile_events;

-- Latest KYC profile per customer (last-write-wins via max updated_at)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_latest_kyc AS
SELECT DISTINCT ON (customer_id)
    customer_id,
    risk_tier,
    kyc_status,
    account_type,
    country_of_residence,
    updated_at
FROM stg_kyc_profiles
ORDER BY customer_id ASC, updated_at DESC;
