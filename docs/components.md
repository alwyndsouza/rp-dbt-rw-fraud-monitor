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

### 4) `dbt-run`
- One-shot dbt runner that deploys all models to RisingWave.
- Runs `dbt run` to create sources and materialized views.
- Manages dependencies automatically via dbt's DAG.

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

## dbt Models

| Directory | Responsibility |
|---|---|
| `fraud_detection/models/sources/` | Kafka source definitions |
| `fraud_detection/models/staging/` | Type casting and enrichment |
| `fraud_detection/models/fraud_signals/` | Pattern-level fraud detection materialized views |
| `fraud_detection/models/risk_aggregations/` | Account-level risk scores, KPI aggregates, exposure views |
| `fraud_detection/models/case_management/` | Fraud case queues and analyst-facing summaries |

All models managed via dbt with proper dependency tracking using `{{ ref() }}` and `{{ source() }}`.

