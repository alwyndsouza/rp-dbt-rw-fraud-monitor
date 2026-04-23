{{ config(materialized='source') }}

CREATE SOURCE IF NOT EXISTS {{ this }} (
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
    properties.bootstrap.server = '{{ env_var("REDPANDA_BROKERS", "redpanda:29092") }}',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
