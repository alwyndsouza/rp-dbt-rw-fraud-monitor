{{ config(materialized='source') }}

CREATE SOURCE IF NOT EXISTS {{ this }} (
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
    properties.bootstrap.server = '{{ env_var("REDPANDA_BROKERS", "redpanda:29092") }}',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
