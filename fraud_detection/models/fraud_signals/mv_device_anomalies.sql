{{ config(materialized='materialized_view') }}

-- SIGNAL 3: Device Anomaly — new device + high-value transaction (> $500)
WITH recent_high_value AS (
    SELECT
        t.customer_id,
        t.transaction_id,
        t.device_id,
        t.amount,
        t.occurred_at
    FROM {{ ref('stg_transactions') }} AS t
    WHERE
        t.amount > 500
        AND t.channel = 'card_not_present'
        AND t.occurred_at >= NOW() - INTERVAL '10 minutes'
),

historical_known_devices AS (
    SELECT DISTINCT
        customer_id,
        device_id
    FROM {{ ref('stg_transactions') }}
    WHERE
        occurred_at >= NOW() - INTERVAL '30 days'
        AND occurred_at < NOW() - INTERVAL '24 hours'
)

SELECT
    t.customer_id,
    t.transaction_id,
    t.device_id,
    t.amount,
    t.occurred_at,
    TRUE AS is_new_device_candidate,
    TRUE AS is_high_value,
    TRUE AS combined_risk_flag
FROM recent_high_value AS t
LEFT JOIN
    historical_known_devices AS d
    ON
        t.customer_id = d.customer_id
        AND t.device_id = d.device_id
WHERE d.device_id IS NULL
