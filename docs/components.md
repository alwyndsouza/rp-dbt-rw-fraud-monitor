# Components Reference

## Runtime Services

### 1) `redpanda`
- Kafka-compatible broker for all event streams.
- Stores topic data in `redpanda_data` volume.
- Health check: `rpk cluster health`.

### 2) `seed-topics`
- One-shot initializer that creates required topics.
- Idempotent by design (`|| true` on existing topics).

### 3) `risingwave`
- Streaming SQL engine.
- Maintains all materialized views for fraud signals, risk, and cases.
- Exposes SQL endpoint (`:4566`) and dashboard (`:5691`).

### 4) `risingwave-init`
- One-shot SQL bootstrap runner.
- Applies `sql/01` through `sql/05` in sequence.

### 5) `producer`
- Python multi-threaded event producer.
- Emits synthetic events at configurable rates.
- Includes health endpoint and minute-tick safety path.

### 6) `redpanda-console`
- Operational UI for browsing topics, messages, and consumer status.

### 7) `grafana`
- Dashboard UI querying RisingWave directly via Postgres datasource.
- Datasource and dashboards are provisioned automatically.

---

## Python Producer Modules

| Module | Responsibility |
|---|---|
| `producers/main.py` | Runtime orchestration, Kafka publishing, health endpoint, worker threads |
| `producers/config.py` | Environment-driven configuration |
| `producers/models.py` | Pydantic event schemas |
| `producers/generators/customer_pool.py` | Synthetic customer/account population |
| `producers/generators/transaction.py` | Transaction and fraud scenario generation |
| `producers/generators/login.py` | Login events and brute-force scenarios |
| `producers/generators/card.py` | Card event generation |
| `producers/generators/alert.py` | Reactive and noise alert generation |
| `producers/generators/kyc_profile.py` | KYC profile event generation |

---

## SQL Modules

| File | Responsibility |
|---|---|
| `sql/01_sources.sql` | Kafka source definitions |
| `sql/02_staging.sql` | Type casting and enrichment |
| `sql/03_fraud_signals.sql` | Pattern-level fraud detection materialized views |
| `sql/04_risk_aggregations.sql` | Account-level risk scores, KPI aggregates, exposure views |
| `sql/05_case_management.sql` | Fraud case queues and analyst-facing summaries |

