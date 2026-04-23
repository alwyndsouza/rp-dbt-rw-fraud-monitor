{{ config(materialized='materialized_view') }}

SELECT
    customer_id,
    risk_tier,
    kyc_status,
    account_type,
    country_of_residence,
    updated_at::TIMESTAMPTZ AS updated_at
FROM {{ ref('kyc_profile_events') }}
