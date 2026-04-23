{{ config(materialized='materialized_view') }}

-- Latest KYC profile per customer (last-write-wins via max updated_at)
SELECT DISTINCT ON (customer_id)
    customer_id,
    risk_tier,
    kyc_status,
    account_type,
    country_of_residence,
    updated_at
FROM {{ ref('stg_kyc_profiles') }}
ORDER BY customer_id ASC, updated_at DESC
