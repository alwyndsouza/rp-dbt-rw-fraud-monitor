# Regulatory Context

This document maps the pipeline's real-time materialized views to the regulatory obligations that motivate them. It is intended for risk engineers and compliance teams evaluating this architecture for production use.

---

## AUSTRAC — Australian Transaction Reports and Analysis Centre

AUSTRAC is Australia's financial intelligence agency and primary AML/CTF regulator under the **Anti-Money Laundering and Counter-Terrorism Financing Act 2006** (AML/CTF Act).

**Key obligations for ADIs and payment service providers:**

1. **Threshold Transaction Reports (TTRs)**: Required for physical currency transactions ≥ AUD $10,000. Must be submitted within 10 business days.

2. **Structuring offence (§142)**: It is a criminal offence to deliberately structure transactions to avoid the TTR threshold. Penalties include up to 5 years imprisonment and substantial civil penalties. AUSTRAC actively pursues structuring cases — the CBA case (2017–2018, $700M settlement) centred partly on failure to detect structuring patterns.

3. **Suspicious Matter Reports (SMRs)**: Required when a reporting entity has reasonable grounds to suspect a transaction is related to money laundering, tax evasion, or other serious offences. There is no minimum amount — an SMR must be filed for any suspicious activity.

4. **International Fund Transfer Instructions (IFTIs)**: All cross-border transfers must be reported to AUSTRAC within 10 business days.

**Pipeline mapping**: `mv_structuring_detection` implements AUSTRAC's structuring typology directly. When this view flags an account, the recommended action in `mv_open_fraud_cases` escalates to `freeze_account` or `escalate`, supporting the SMR obligation timeline.

---

## PCI-DSS — Payment Card Industry Data Security Standard

PCI-DSS is an industry mandate (not a law) enforced by card networks (Visa, Mastercard) through acquirer agreements. Non-compliance results in fines and potential loss of card acceptance privileges.

**CNP fraud context**: Card-not-present transactions are the highest-risk channel because the merchant cannot verify physical card possession. With global chip-and-PIN adoption reducing card-present fraud, CNP fraud grew to represent >85% of card fraud losses in Australia by 2023 (per the Australian Payments Network annual report).

**Relevant requirements:**

- **Req 10**: Implement logging and monitoring to detect and minimise the impact of data compromise. Covers real-time anomaly detection for unusual access patterns.
- **Req 11.5**: Change detection mechanisms and alerting for critical system files.
- **Req 12.10**: Incident response plan must include procedures for "compromised cardholder data environments" — which in practice means detecting CNP spikes promptly.

**Pipeline mapping**: `mv_cnp_spike` and `mv_velocity_alerts` directly implement the continuous CNP monitoring implied by Req 10. The `mv_fraud_kpis_1min` view provides the audit-ready metrics that support PCI-DSS compliance reporting.

---

## APRA CPS 234 — Information Security (Australian Prudential Regulation Authority)

CPS 234 became effective from 1 July 2019 and applies to all APRA-regulated entities including banks, insurance companies, and superannuation funds. It establishes mandatory information security obligations.

**Key requirements:**

- **§36**: An APRA-regulated entity must have mechanisms to detect and respond to information security incidents in a timely manner.
- **§37**: Maintain an information security capability commensurate with the size, nature, and complexity of threats faced.
- **§38**: Implement controls to protect information assets and regularly test those controls.
- **Notification**: Material incidents must be reported to APRA within 72 hours.

**Pipeline mapping**: `mv_login_failure_storm` (brute force detection) and `mv_device_anomalies` (account takeover detection) are the primary implementations of §36's "timely detection" obligation. The `mv_open_fraud_cases` view with `recommended_action = 'escalate'` supports the 72-hour notification workflow by surfacing critical incidents immediately.

---

## FATF Recommendations — Financial Action Task Force

FATF is the international standard-setting body for AML/CTF policy. Its 40 Recommendations form the basis for domestic legislation in 200+ jurisdictions including Australia's AML/CTF Act.

**Relevant recommendations:**

- **Recommendation 10**: Customer due diligence (CDD) — knowing your customer's risk tier informs transaction monitoring thresholds. Maps to `mv_latest_kyc` and the `kyc_risk_tier` join in `mv_open_fraud_cases`.

- **Recommendation 20**: Suspicious transaction reporting — financial institutions must file STRs/SMRs when they suspect money laundering. The `mv_correlated_alert_burst` view is designed to surface the multi-indicator patterns that FATF's typologies describe as "red flags" warranting STR filing.

- **Recommendation 16**: Wire transfer transparency requirements — cross-border transfer monitoring. The `mv_geo_impossible_trips` view provides geographic anomaly detection that supports Rec 16 compliance for international payment corridors.

---

## How This Pipeline Supports Real-Time SMR Obligations

A Suspicious Matter Report in Australia must be filed "as soon as practicable" after forming a suspicion — typically within 3 business days for most matters, or immediately for terrorism financing.

The pipeline's case management layer (`mv_open_fraud_cases`) maps directly to this workflow:

| Risk Score | Recommended Action | SMR Implication |
|---|---|---|
| > 0.9 or PEP/sanctioned | `escalate` | Immediate SMR review required |
| > 0.75 + structuring | `freeze_account` | SMR filing within 24 hours |
| > 0.6 + velocity/CNP | `block_card` | SMR review within 3 days |
| ≤ 0.6 | `monitor` | Watchlist; no immediate SMR |

In a production implementation, the `escalate` cases would trigger an automated workflow to the compliance team's case management system (e.g. NICE Actimize, Quantexa, or an internal system), with the `contributing_signals` array providing the factual basis for the SMR narrative.
