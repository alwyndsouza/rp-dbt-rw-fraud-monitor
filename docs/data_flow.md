# Data Flow and Lineage

## End-to-End Pipeline

```text
Producer Events
  -> Redpanda Topics
    -> RisingWave Sources
      -> Staging MVs
        -> Fraud Signal MVs
          -> Risk Aggregation MVs
            -> Case Management MVs
              -> Grafana Dashboards / Analyst Queries
```

## Topic-to-Source Mapping

| Topic | RisingWave Source | Purpose |
|---|---|---|
| `transactions` | `transactions` | Primary transaction stream for most fraud detection logic |
| `login_events` | `login_events` | Authentication anomalies and brute-force signals |
| `card_events` | `card_events` | Card lifecycle and fraud-system actions |
| `alert_events` | `alert_events` | Correlation of independent fraud alerts |
| `kyc_profile_events` | `kyc_profile_events` | Customer risk context for case prioritization |
| `fraud_dlq` | N/A (currently sink-only) | Publish-failure safety path from producer |

## SQL Model Layers

### Layer 1 — Sources (`sql/01_sources.sql`)
- Ingests raw JSON from Kafka-compatible topics.
- Minimal transformation at this stage.
- `scan.startup.mode = 'earliest'` enables replay from beginning.

### Layer 2 — Staging (`sql/02_staging.sql`)
- Casts raw timestamps into `TIMESTAMPTZ`.
- Adds helper flags:
  - `is_odd_hours`
  - `is_cnp`
  - `is_high_risk_mcc`
- Maintains latest customer KYC view (`mv_latest_kyc`).

### Layer 3 — Fraud Signals (`sql/03_fraud_signals.sql`)
Independent MVs implement fraud typologies:
- `mv_velocity_alerts`
- `mv_geo_impossible_trips`
- `mv_device_anomalies`
- `mv_cnp_spike`
- `mv_login_failure_storm`
- `mv_structuring_detection`
- `mv_correlated_alert_burst`
- `mv_network_analysis` (stretch signal)

### Layer 4 — Risk Aggregation (`sql/04_risk_aggregations.sql`)
- Combines signal flags into account-level risk score (`mv_account_risk_score_realtime`).
- Produces operational KPI and exposure views for dashboards.

### Layer 5 — Case Management (`sql/05_case_management.sql`)
- Produces analyst action queues and alert summaries:
  - `mv_open_fraud_cases`
  - `mv_resolved_cases_today`
  - `mv_recent_high_alerts`

## Data Quality Considerations

1. **Schema Drift Risk**
   - Source field changes can silently break casts/logic.
   - Mitigation: add schema contract checks in CI and canary events.

2. **Event Time Integrity**
   - Windowed logic depends on valid UTC timestamps.
   - Mitigation: enforce producer-side timestamp format tests + null rejection checks.

3. **Duplicate Events**
   - At-least-once delivery can inflate counts.
   - Mitigation: add dedupe strategy using event IDs in staging when needed.

4. **Late Events**
   - Tumbling windows may undercount if events arrive late.
   - Mitigation: define acceptable lateness + watermark strategy for production.

## Recommended Data Testing Strategy

- **Unit tests (Python):** generator schema and fraud scenario invariants.
- **SQL assertion tests:** row-level expectations on signal views after deterministic seed runs.
- **Freshness tests:** max event age per source and per key MV.
- **Reconciliation tests:** transaction counts source vs staging over aligned windows.

