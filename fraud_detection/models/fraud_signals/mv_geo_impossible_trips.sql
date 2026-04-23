{{ config(materialized='materialized_view') }}

-- SIGNAL 2: Geographic Impossibility — consecutive txns > 1000km in < 2 hours
-- Uses LAG() to compare current vs previous transaction location per customer.
WITH ordered_txns AS (
    SELECT
        customer_id,
        transaction_id,
        country_code,
        latitude,
        longitude,
        occurred_at,
        LAG(transaction_id) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_txn_id,
        LAG(country_code) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_country,
        LAG(latitude) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_lat,
        LAG(longitude) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_lon,
        LAG(occurred_at) OVER (
            PARTITION BY customer_id
            ORDER BY occurred_at
        ) AS prev_occurred_at
    FROM {{ ref('stg_transactions') }}
),

with_distance AS (
    SELECT
        customer_id,
        transaction_id AS txn2_id,
        country_code AS txn2_country,
        latitude AS txn2_lat,
        longitude AS txn2_lon,
        occurred_at AS txn2_time,
        prev_txn_id AS txn1_id,
        prev_country AS txn1_country,
        prev_lat AS txn1_lat,
        prev_lon AS txn1_lon,
        prev_occurred_at AS txn1_time,
        -- Haversine approximation: 1 degree lat ≈ 111km
        SQRT(
            POWER((latitude - prev_lat) * 111.0, 2)
            + POWER((longitude - prev_lon) * 111.0 * ABS(COS(RADIANS((latitude + prev_lat) / 2))), 2)
        ) AS approx_distance_km,
        EXTRACT(EPOCH FROM (occurred_at - prev_occurred_at)) / 60.0 AS time_diff_minutes
    FROM ordered_txns
    WHERE
        prev_txn_id IS NOT NULL
        AND prev_lat IS NOT NULL
)

SELECT
    customer_id,
    txn1_id,
    txn1_country,
    txn1_lat,
    txn1_lon,
    txn1_time,
    txn2_id,
    txn2_country,
    txn2_lat,
    txn2_lon,
    txn2_time,
    ROUND(approx_distance_km::NUMERIC, 2) AS approx_distance_km,
    ROUND(time_diff_minutes::NUMERIC, 2) AS time_diff_minutes,
    (approx_distance_km > 1000 AND time_diff_minutes < 120 AND time_diff_minutes > 0) AS is_impossible
FROM with_distance
WHERE approx_distance_km > 500
