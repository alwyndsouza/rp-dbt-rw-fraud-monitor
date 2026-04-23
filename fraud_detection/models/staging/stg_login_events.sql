{{ config(materialized='materialized_view') }}

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
FROM {{ ref('login_events') }}
