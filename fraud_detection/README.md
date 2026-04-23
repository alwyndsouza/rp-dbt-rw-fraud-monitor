# fraud_detection — dbt Project

This dbt project manages all RisingWave materialized views and Kafka sources for the fraud detection pipeline using the [`dbt-risingwave`](https://github.com/risingwavelabs/dbt-risingwave) adapter.

## Project Structure

```
fraud_detection/
├── dbt_project.yml          ← project config + materialization defaults
├── profiles.yml             ← connection profile (reads env vars)
├── models/
│   ├── sources/             ← Kafka source definitions (materialized: source)
│   │   ├── transactions.sql
│   │   ├── login_events.sql
│   │   ├── card_events.sql
│   │   ├── alert_events.sql
│   │   └── kyc_profile_events.sql
│   ├── staging/             ← type casts + derived columns (materialized_view)
│   │   ├── stg_transactions.sql
│   │   ├── stg_login_events.sql
│   │   ├── stg_card_events.sql
│   │   ├── stg_alert_events.sql
│   │   ├── stg_kyc_profiles.sql
│   │   └── mv_latest_kyc.sql
│   ├── fraud_signals/       ← real-time fraud detection MVs
│   │   ├── mv_velocity_alerts.sql
│   │   ├── mv_geo_impossible_trips.sql
│   │   ├── mv_known_customer_devices.sql
│   │   ├── mv_device_anomalies.sql
│   │   ├── mv_cnp_spike.sql
│   │   ├── mv_login_failure_storm.sql
│   │   ├── mv_structuring_detection.sql
│   │   ├── mv_correlated_alert_burst.sql
│   │   └── mv_network_analysis.sql
│   ├── risk_aggregations/   ← risk scoring + operational KPIs
│   │   ├── mv_account_risk_score_realtime.sql
│   │   ├── mv_fraud_kpis_1min.sql
│   │   ├── mv_merchant_fraud_exposure.sql
│   │   ├── mv_channel_risk_breakdown.sql
│   │   └── mv_hourly_fraud_trend.sql
│   └── case_management/     ← investigation queue + actions
│       ├── mv_open_fraud_cases.sql
│       ├── mv_resolved_cases_today.sql
│       └── mv_recent_high_alerts.sql
```

## Prerequisites

- Python ≥ 3.11
- `dbt-risingwave` adapter: `pip install dbt-risingwave>=1.9.7`
- RisingWave running and reachable

## Local Development

```bash
# Install the adapter
pip install dbt-risingwave>=1.9.7

# Validate connection
make dbt-debug

# Run all models
make dbt-run

# Run tests
make dbt-test

# Generate and serve docs
make dbt-docs
```

Or run directly inside the `fraud_detection/` directory:

```bash
cd fraud_detection

# Check connection
dbt debug --profiles-dir .

# Build all models (sources → staging → signals → risk → cases)
dbt run --profiles-dir .

# Run a specific layer only
dbt run --select fraud_signals --profiles-dir .

# Generate docs
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
```

## Connection (profiles.yml)

The `profiles.yml` in this directory reads connection details from environment variables with sensible defaults for the local Docker Compose stack:

| Variable            | Default          | Description              |
|---------------------|------------------|--------------------------|
| `RISINGWAVE_HOST`   | `localhost`      | RisingWave host          |
| `RISINGWAVE_PORT`   | `4566`           | RisingWave PostgreSQL port |
| `RISINGWAVE_USER`   | `root`           | Database user            |
| `RISINGWAVE_PASSWORD` | *(empty)*      | Database password        |
| `RISINGWAVE_DB`     | `dev`            | Database name            |
| `REDPANDA_BROKERS`  | `redpanda:29092` | Kafka bootstrap servers  |

For production, copy `profiles.yml` to `~/.dbt/profiles.yml` and set the appropriate environment variables (or fill in the values directly).

## Materialization Types

| Layer            | Materialization    | RisingWave Object         |
|------------------|--------------------|---------------------------|
| `sources/`       | `source`           | `CREATE SOURCE`           |
| `staging/`       | `materialized_view`| `CREATE MATERIALIZED VIEW`|
| `fraud_signals/` | `materialized_view`| `CREATE MATERIALIZED VIEW`|
| `risk_aggregations/` | `materialized_view` | `CREATE MATERIALIZED VIEW` |
| `case_management/` | `materialized_view` | `CREATE MATERIALIZED VIEW` |

## Docker Compose

In the Docker Compose stack, the `dbt-run` service automatically runs `dbt run` after RisingWave and Redpanda are healthy. The producer waits for `dbt-run` to complete before starting.

```bash
make up        # starts all services including dbt-run
make dbt-run   # re-run dbt models locally (requires dbt-risingwave installed)
```
