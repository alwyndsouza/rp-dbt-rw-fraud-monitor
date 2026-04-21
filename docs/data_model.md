# Data Model

## Event Schemas

Full field-level documentation for all five event types produced and consumed by the pipeline.

### `transaction_event` — Topic: `transactions`

| Field | Type | Example | Description |
|---|---|---|---|
| `transaction_id` | UUID string | `txn_a1b2c3` | Globally unique transaction identifier |
| `account_id` | UUID string | `acc_x9y8z7` | Bank account identifier |
| `customer_id` | UUID string | `cust_m3n4o5` | Customer identifier (may own multiple accounts) |
| `amount` | float | `249.95` | Transaction amount in `currency` units |
| `currency` | string | `AUD` | ISO 4217 currency code |
| `merchant_id` | UUID string | `merch_p6q7r8` | Merchant identifier |
| `merchant_category_code` | string | `5411` | ISO 18245 Merchant Category Code |
| `merchant_name` | string | `Woolworths Sydney` | Human-readable merchant name |
| `channel` | enum | `card_present` | Payment channel: `card_present`, `card_not_present`, `atm`, `transfer` |
| `card_last4` | string | `4821` | Last 4 digits of card (PAN truncation per PCI-DSS) |
| `device_id` | UUID string | `dev_s9t0u1` | Device fingerprint identifier |
| `ip_address` | string | `203.45.67.89` | IPv4 address at time of transaction |
| `latitude` | float | `-33.8688` | Transaction location latitude (WGS84) |
| `longitude` | float | `151.2093` | Transaction location longitude (WGS84) |
| `country_code` | string | `AU` | ISO 3166-1 alpha-2 country code |
| `occurred_at` | ISO-8601 string | `2026-04-18T10:22:31.456Z` | Transaction initiation timestamp (UTC) |
| `status` | enum | `pending` | Transaction status: `pending`, `approved`, `declined` |

**MCC examples used in fraud detection:**
| MCC | Category | Fraud Relevance |
|---|---|---|
| `5411` | Grocery Stores | Baseline / normal spend |
| `5812` | Restaurants | Baseline / normal spend |
| `6011` | ATM Cash Withdrawal | High-risk (structuring, unusual hours) |
| `7995` | Gambling | High-risk (unusual MCC pattern) |
| `6051` | Crypto Exchange | High-risk (AML exposure) |

---

### `login_event` — Topic: `login_events`

| Field | Type | Example | Description |
|---|---|---|---|
| `event_id` | UUID string | `evt_v2w3x4` | Unique event identifier |
| `customer_id` | UUID string | `cust_m3n4o5` | Customer attempting login |
| `device_id` | UUID string | `dev_s9t0u1` | Device fingerprint |
| `ip_address` | string | `203.45.67.89` | Source IP address |
| `country_code` | string | `AU` | Resolved country of source IP |
| `latitude` | float | `-33.8688` | Approximate source latitude |
| `longitude` | float | `151.2093` | Approximate source longitude |
| `user_agent` | string | `Mozilla/5.0…` | Browser/client user agent string |
| `success` | boolean | `false` | Whether login succeeded |
| `failure_reason` | string or null | `wrong_password` | Failure reason if `success=false` |
| `occurred_at` | ISO-8601 string | `2026-04-18T10:20:00.000Z` | Event timestamp (UTC) |

---

### `card_event` — Topic: `card_events`

| Field | Type | Example | Description |
|---|---|---|---|
| `event_id` | UUID string | `evt_y5z6a7` | Unique event identifier |
| `account_id` | UUID string | `acc_x9y8z7` | Account the card belongs to |
| `customer_id` | UUID string | `cust_m3n4o5` | Card owner |
| `card_last4` | string | `4821` | Last 4 digits of affected card |
| `event_type` | enum | `block` | `block`, `unblock`, `reissue`, `pin_change`, `limit_change` |
| `initiated_by` | enum | `fraud_system` | `customer`, `bank`, `fraud_system` |
| `occurred_at` | ISO-8601 string | `2026-04-18T10:23:00.000Z` | Event timestamp (UTC) |

---

### `alert_event` — Topic: `alert_events`

| Field | Type | Example | Description |
|---|---|---|---|
| `alert_id` | UUID string | `alt_b8c9d0` | Unique alert identifier |
| `customer_id` | UUID string | `cust_m3n4o5` | Affected customer |
| `transaction_id` | UUID string | `txn_a1b2c3` | Triggering transaction (if applicable) |
| `alert_type` | enum | `velocity` | See alert types below |
| `severity` | enum | `high` | `low`, `medium`, `high`, `critical` |
| `confidence_score` | float | `0.87` | Model/rule confidence (0.0–1.0) |
| `rule_id` | string | `RULE_042` | Rule or model identifier |
| `occurred_at` | ISO-8601 string | `2026-04-18T10:22:32.100Z` | Alert generation timestamp (UTC) |

**Alert types:**
| Alert Type | Detection View | Typical Confidence |
|---|---|---|
| `velocity` | `mv_velocity_alerts` | 0.75–0.92 |
| `geo_anomaly` | `mv_geo_impossible_trips` | 0.85–0.99 |
| `account_takeover` | `mv_device_anomalies` | 0.88–0.99 |
| `card_not_present` | `mv_cnp_spike` | 0.75–0.93 |
| `device_fingerprint` | `mv_device_anomalies` | 0.60–0.82 |
| `structuring` | `mv_structuring_detection` | 0.80–0.97 |

---

### `kyc_profile_event` — Topic: `kyc_profile_events`

| Field | Type | Example | Description |
|---|---|---|---|
| `customer_id` | UUID string | `cust_m3n4o5` | Customer identifier |
| `risk_tier` | enum | `medium` | `low`, `medium`, `high`, `pep`, `sanctioned` |
| `kyc_status` | enum | `verified` | `verified`, `pending`, `failed`, `expired` |
| `account_type` | enum | `personal` | `personal`, `business`, `joint` |
| `country_of_residence` | string | `AU` | ISO 3166-1 alpha-2 |
| `updated_at` | ISO-8601 string | `2026-04-18T09:00:00.000Z` | Profile update timestamp (UTC) |

**Risk tier distribution in synthetic customer pool:**
| Tier | Proportion | Description |
|---|---|---|
| `low` | 80% | Standard retail customers |
| `medium` | 15% | Elevated monitoring required |
| `high` | 4% | Enhanced due diligence required |
| `pep` | 1% | Politically Exposed Person — immediate escalation |
| `sanctioned` | <0.1% | OFAC/UN sanctions list match |
