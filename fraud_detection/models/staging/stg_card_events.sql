{{ config(materialized='materialized_view') }}

SELECT
    event_id,
    account_id,
    customer_id,
    card_last4,
    event_type,
    initiated_by,
    occurred_at::TIMESTAMPTZ AS occurred_at
FROM {{ ref('card_events') }}
