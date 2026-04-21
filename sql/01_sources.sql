-- =============================================================================
-- 01_sources.sql — Redpanda (Kafka) Source Definitions
-- RisingWave ingests raw JSON from Redpanda topics via these sources.
-- =============================================================================

CREATE SOURCE IF NOT EXISTS transactions (
    transaction_id          VARCHAR,
    account_id              VARCHAR,
    customer_id             VARCHAR,
    amount                  DOUBLE PRECISION,
    currency                VARCHAR,
    merchant_id             VARCHAR,
    merchant_category_code  VARCHAR,
    merchant_name           VARCHAR,
    channel                 VARCHAR,
    card_last4              VARCHAR,
    device_id               VARCHAR,
    ip_address              VARCHAR,
    latitude                DOUBLE PRECISION,
    longitude               DOUBLE PRECISION,
    country_code            VARCHAR,
    occurred_at             VARCHAR,
    status                  VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'transactions',
    properties.bootstrap.server = 'redpanda:29092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

CREATE SOURCE IF NOT EXISTS login_events (
    event_id        VARCHAR,
    customer_id     VARCHAR,
    device_id       VARCHAR,
    ip_address      VARCHAR,
    country_code    VARCHAR,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    user_agent      VARCHAR,
    success         BOOLEAN,
    failure_reason  VARCHAR,
    occurred_at     VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'login_events',
    properties.bootstrap.server = 'redpanda:29092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

CREATE SOURCE IF NOT EXISTS card_events (
    event_id        VARCHAR,
    account_id      VARCHAR,
    customer_id     VARCHAR,
    card_last4      VARCHAR,
    event_type      VARCHAR,
    initiated_by    VARCHAR,
    occurred_at     VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'card_events',
    properties.bootstrap.server = 'redpanda:29092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

CREATE SOURCE IF NOT EXISTS alert_events (
    alert_id            VARCHAR,
    customer_id         VARCHAR,
    transaction_id      VARCHAR,
    alert_type          VARCHAR,
    severity            VARCHAR,
    confidence_score    DOUBLE PRECISION,
    rule_id             VARCHAR,
    occurred_at         VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'alert_events',
    properties.bootstrap.server = 'redpanda:29092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;

CREATE SOURCE IF NOT EXISTS kyc_profile_events (
    customer_id             VARCHAR,
    risk_tier               VARCHAR,
    kyc_status              VARCHAR,
    account_type            VARCHAR,
    country_of_residence    VARCHAR,
    updated_at              VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'kyc_profile_events',
    properties.bootstrap.server = 'redpanda:29092',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
