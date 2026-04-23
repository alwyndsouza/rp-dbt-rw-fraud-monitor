{{ config(materialized='source') }}

CREATE SOURCE IF NOT EXISTS {{ this }} (
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
    properties.bootstrap.server = '{{ env_var("REDPANDA_BROKERS", "redpanda:29092") }}',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
