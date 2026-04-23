{{ config(materialized='source') }}

CREATE SOURCE IF NOT EXISTS {{ this }} (
    customer_id             VARCHAR,
    risk_tier               VARCHAR,
    kyc_status              VARCHAR,
    account_type            VARCHAR,
    country_of_residence    VARCHAR,
    updated_at              VARCHAR
) WITH (
    connector = 'kafka',
    topic = 'kyc_profile_events',
    properties.bootstrap.server = '{{ env_var("REDPANDA_BROKERS", "redpanda:29092") }}',
    scan.startup.mode = 'earliest'
) FORMAT PLAIN ENCODE JSON;
