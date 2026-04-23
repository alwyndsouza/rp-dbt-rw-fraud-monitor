{{ config(materialized='source') }}

CREATE SOURCE IF NOT EXISTS {{ this }} (
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
    properties.bootstrap.server = '{{ env_var("REDPANDA_BROKERS", "redpanda:29092") }}',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
