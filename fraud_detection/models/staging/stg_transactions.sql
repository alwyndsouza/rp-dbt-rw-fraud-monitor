{{ config(materialized='materialized_view') }}

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
    (EXTRACT(HOUR FROM occurred_at::TIMESTAMPTZ) BETWEEN 2 AND 4) AS is_odd_hours,
    (channel = 'card_not_present') AS is_cnp,
    (merchant_category_code IN ('6011', '7995', '6051')) AS is_high_risk_mcc
FROM {{ ref('transactions') }}
