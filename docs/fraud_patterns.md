# Fraud Pattern Documentation

This document describes each fraud pattern detected by the pipeline, including real-world context, detection logic, signal latency, false positive risk, and regulatory references.

---

## Pattern 1: Velocity Fraud

### Real-World Description
Fraudsters who obtain card credentials (via phishing, data breaches, or skimming) typically run rapid small-amount tests before attempting high-value transactions. The pattern involves many card-not-present charges in a short burst — often at the same merchant or category — to validate the card is live before the cardholder notices.

### Detection Logic
`mv_velocity_alerts` uses a 60-second tumbling window grouped by `account_id`. When a single account generates ≥5 transactions within the window, `is_velocity_breach = TRUE`. The card-not-present channel weighting further elevates this signal in the risk score.

```sql
-- Core detection
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '60' SECOND)
GROUP BY account_id, card_last4, window_start, window_end
HAVING COUNT(*) >= 5
```

Risk score contribution: **+0.25**

### Signal Latency
**≤ 60 seconds** from first transaction in burst — the window closes and the MV updates at each tumble boundary.

### False Positive Risk
**Medium.** Legitimate subscription services, loyalty point redemptions, or automated payment reconciliation may trigger this pattern. Mitigation: combine with `is_cnp` filter and cross-reference against `mv_latest_kyc` business accounts.

### Regulatory Reference
- **PCI-DSS Requirement 10.2**: Automated audit trails for all access to cardholder data and all invalid access attempts.
- **APRA CPS 234**: Continuous monitoring of information security controls.

---

## Pattern 2: Geographic Impossibility

### Real-World Description
A transaction appearing in Sydney at 10:00am and then in London at 11:30am is physically impossible. This pattern indicates one of: (a) card cloning — the physical card was copied and used overseas, (b) account sharing — credentials shared with someone in another country, or (c) VPN/proxy bypass attempts where the IP address country differs from the physical terminal.

### Detection Logic
`mv_geo_impossible_trips` uses `LAG()` over a customer partition ordered by `occurred_at` to compare consecutive transaction coordinates. The Haversine approximation formula calculates great-circle distance:

```sql
SQRT(
    POWER((latitude - prev_lat) * 111.0, 2) +
    POWER((longitude - prev_lon) * 111.0 * ABS(COS(RADIANS((latitude + prev_lat) / 2))), 2)
) AS approx_distance_km
```

Flag: `distance_km > 1000 AND time_diff_minutes < 120 AND time_diff_minutes > 0`

Risk score contribution: **+0.30**

### Signal Latency
**< 1 second** — triggered immediately on the second transaction using LAG-based stream processing.

### False Positive Risk
**Low.** Legitimate geographic impossibility is rare for card-present transactions. CNP transactions from home while travelling may create false flags when the cardholder uses their physical card and online account simultaneously. Mitigation: require `channel = 'card_present'` for highest confidence.

### Regulatory Reference
- **APRA CPS 234**: Anomaly detection requirements.
- **FATF Recommendation 16**: Wire transfer monitoring covering geographic anomalies.

---

## Pattern 3: Account Takeover

### Real-World Description
Account takeover (ATO) follows a predictable chain: attacker acquires credentials (phishing/breach) → attempts login (often with credential stuffing) → gains access → initiates high-value transaction from a new device. The combination of a new device fingerprint plus a high-value CNP transaction is the strongest single signal for ATO.

### Detection Logic
`mv_device_anomalies` identifies transactions where:
1. `amount > 500` (high-value threshold)
2. `channel = 'card_not_present'`
3. Transaction is recent (within 10 minutes)

The brute force login signal (`mv_login_failure_storm`) provides corroborating evidence when a login failure storm precedes the transaction for the same `customer_id`.

Risk score contribution: **device anomaly +0.20**, **brute force +0.35** (combined: 0.55 before other signals)

### Signal Latency
**< 1 second** for device anomaly detection. Brute force signal adds within **60 seconds** of the login storm.

### False Positive Risk
**Medium.** Customers purchasing on a new laptop or work device will trigger device anomaly. Mitigation: lower confidence if the IP resolves to the customer's home ISP range, or require both brute-force AND device signals together.

### Regulatory Reference
- **APRA CPS 234**: Incident detection and response obligations for ADIs.
- **OWASP ASVS Level 2**: Authentication monitoring requirements.

---

## Pattern 4: Card-Not-Present Spike

### Real-World Description
CNP fraud is the dominant fraud vector in countries with chip-and-PIN adoption (including Australia post-2014). Once a fraudster has card details (number, expiry, CVV — often harvested via e-commerce skimmers or data breaches), they make rapid online purchases before the cardholder or bank notices. Amounts often escalate as confidence grows.

### Detection Logic
`mv_cnp_spike` uses a 5-minute tumbling window filtered to `is_cnp = TRUE`, flagging cards with ≥8 CNP transactions within the window:

```sql
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '5' MINUTE)
WHERE is_cnp = TRUE
GROUP BY card_last4, account_id, window_start, window_end
HAVING COUNT(*) >= 8
```

Risk score contribution: **+0.15**

### Signal Latency
**≤ 5 minutes** — bounded by the tumbling window size.

### False Positive Risk
**Medium-High.** Automated recurring payments or bulk online orders may resemble a CNP spike. Mitigation: check merchant diversity — a legitimate spike spans many merchants, while fraud concentrates on a few (or one) merchant category.

### Regulatory Reference
- **PCI-DSS Requirement 12.10**: Incident response procedures specifically covering CNP fraud.
- **Australian Payments Network (APN) CNP Fraud Mitigation Framework**: Industry-standard controls for CNP risk.

---

## Pattern 5: Brute Force Login

### Real-World Description
Credential stuffing attacks use automated tools to test username/password combinations from breach databases at high speed. A typical attack generates 3–10 failed login attempts per target within seconds, originating from a single IP or rotating proxy network, before either succeeding or moving to the next target.

### Detection Logic
`mv_login_failure_storm` uses a 60-second tumbling window on `stg_login_events` where `success = FALSE`, flagging customers with ≥3 failures:

```sql
FROM TUMBLE(stg_login_events, occurred_at, INTERVAL '60' SECOND)
WHERE success = FALSE
GROUP BY customer_id, window_start, window_end
HAVING COUNT(*) >= 3
```

Additional signals: `COUNT(DISTINCT ip_address)` and `COUNT(DISTINCT device_id)` distinguish distributed attacks from a single locked-out user.

Risk score contribution: **+0.35** (highest individual weight — ATO precursor)

### Signal Latency
**≤ 60 seconds** from first failed attempt.

### False Positive Risk
**Low-Medium.** A user who genuinely forgets their password may trigger this if they try multiple times quickly. Mitigation: require `distinct_ips > 1` OR `distinct_devices > 1` for high-confidence brute-force classification (a real user is on one device).

### Regulatory Reference
- **APRA CPS 234 §36**: ADIs must detect information security incidents promptly.
- **NIST SP 800-63B**: Digital identity authentication assurance level guidance.

---

## Pattern 6: Structuring / Smurfing

### Real-World Description
Structuring is the deliberate practice of breaking large cash transactions into smaller amounts to evade financial intelligence reporting thresholds. In Australia, AUSTRAC requires Threshold Transaction Reports (TTRs) for transactions ≥ AUD $10,000. Structurers typically use amounts like $9,800 or $9,750 — "just below the threshold." This is a criminal offence under Section 142 of the AML/CTF Act 2006 with penalties up to 5 years imprisonment.

### Detection Logic
`mv_structuring_detection` uses a 60-minute tumbling window, flagging accounts with ≥2 transactions in the range `$9,000–$9,999`:

```sql
FROM TUMBLE(stg_transactions, occurred_at, INTERVAL '60' MINUTE)
WHERE amount BETWEEN 9000 AND 9999
GROUP BY account_id, customer_id, window_start, window_end
HAVING COUNT(*) >= 2
```

The `STRUCTURING_THRESHOLD` environment variable allows the detection band to be adjusted for other jurisdictions (US: $10,000 USD, UK: £10,000).

Risk score contribution: **+0.40** (highest weight — direct AML obligation)

### Signal Latency
**≤ 60 minutes** — bounded by the window. The signal fires when the second qualifying transaction appears within the window.

### False Positive Risk
**Low.** Two $9,500 cash withdrawals within an hour is highly unusual for legitimate behaviour. Mitigation: cross-reference with `mv_latest_kyc` for business accounts that may have legitimate high-frequency cash needs (e.g. retail businesses doing end-of-day banking).

### Regulatory Reference
- **AUSTRAC AML/CTF Act 2006 §142**: Structuring offence.
- **FATF Recommendation 20**: Suspicious transaction reporting obligations.
- **AUSTRAC Guidance Note GN 09/2018**: Structuring typologies for reporting entities.

---

## Pattern 7: Compound Fraud

### Real-World Description
Sophisticated fraud events rarely trigger just one signal in isolation. A coordinated account takeover, for example, produces: failed logins → new device transaction → geographic anomaly → high-value CNP spike — all within minutes. The co-occurrence of multiple fraud typologies on the same customer within a short window is itself a strong indicator of a coordinated fraud event, and warrants immediate escalation even when individual signals are below threshold.

### Detection Logic
`mv_correlated_alert_burst` uses a 5-minute tumbling window on `stg_alert_events`, flagging customers with ≥2 distinct `alert_type` values:

```sql
FROM TUMBLE(stg_alert_events, occurred_at, INTERVAL '5' MINUTE)
GROUP BY customer_id, window_start, window_end
HAVING COUNT(DISTINCT alert_type) >= 2
```

The `max_confidence_score` field captures the highest-confidence alert in the burst, supporting triage prioritisation.

Risk score contribution: **+0.20**

### Signal Latency
**≤ 5 minutes** — bounded by the alert correlation window.

### False Positive Risk
**Low.** Two unrelated alert types co-occurring on the same customer in 5 minutes is rare for legitimate behaviour. Mitigation: check whether the alerts originate from the same or different `rule_id` families.

### Regulatory Reference
- **FATF Recommendation 20**: Suspicious matter reporting.
- **AUSTRAC SMR guidance**: Multi-indicator suspicious matter reports carry higher regulatory weight.
- **APRA CPS 234**: Correlated incident detection requirements.
