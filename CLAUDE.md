# fraud-detection-streaming

Real-time banking fraud detection pipeline using **Redpanda → RisingWave → Grafana**. Detects 7 fraud patterns (velocity, geo-impossibility, account takeover, CNP spike, brute-force login, AML structuring, compound fraud) with sub-300ms signal latency. No cloud dependencies.

---

## Architecture in One Paragraph

A Python producer generates synthetic banking events (transactions, logins, card events, alerts, KYC profiles) at configurable rates and publishes them to **Redpanda** topics. **RisingWave** continuously consumes those topics via Kafka sources and maintains 18 materialized views across 5 SQL layers: sources → staging → fraud signals → risk aggregations → case management. An account-level risk score (0.0–1.0) is computed from 7 additive signal weights. **Grafana** queries RisingWave directly via its PostgreSQL datasource for a live "Fraud Operations Centre" dashboard, auto-provisioned at startup with 10-second refresh.

---

## Repo Layout

```
fraud-detection-streaming/
├── CLAUDE.md                  ← you are here
├── docker-compose.yml         ← 6 services, all health-checked
├── Makefile                   ← developer commands
├── .env.example               ← all config lives here
├── pyproject.toml             ← root ruff + pytest config
│
├── producers/                 ← Python event producer
│   ├── main.py                ← entrypoint; starts 5 producer threads
│   ├── config.py              ← env-var config
│   ├── models.py              ← Pydantic v2 event schemas
│   ├── pyproject.toml         ← producer-level ruff + uv deps
│   ├── generators/
│   │   ├── customer_pool.py   ← 500 synthetic customers with stable profiles
│   │   ├── transaction.py     ← normal + 6 fraud scenario generators
│   │   ├── login.py           ← normal + brute-force login generators
│   │   ├── card.py            ← card lifecycle events
│   │   ├── alert.py           ← reactive alerts + noise alerts
│   │   └── kyc_profile.py     ← KYC profile events
│   └── tests/                 ← 75 pytest tests, all must pass
│
├── fraud_detection/           ← dbt project for RisingWave
│   ├── dbt_project.yml        ← dbt project config
│   ├── profiles.yml           ← RisingWave connection profile
│   └── models/
│       ├── sources/           ← Kafka source definitions (FORMAT PLAIN ENCODE JSON)
│       ├── staging/           ← type casting + derived columns
│       ├── fraud_signals/     ← 8 fraud detection MVs (TUMBLE/HOP/LAG)
│       ├── risk_aggregations/ ← risk score, KPIs, merchant/channel breakdown
│       └── case_management/   ← investigation queue + recommended actions
│
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/risingwave.yml  ← auto-provisions RisingWave PostgreSQL datasource
│   │   └── dashboards/fraud.yml        ← tells Grafana where to load dashboards from
│   └── dashboards/
│       └── fraud_ops_centre.json       ← Fraud Operations Centre dashboard
│
├── scripts/
│   ├── check_pipeline.sh      ← end-to-end health check
│   └── redpanda-console-config.yaml   ← Redpanda Console UI config
│
└── docs/
    ├── architecture.md
    ├── fraud_patterns.md      ← all 7 patterns documented
    ├── regulatory_context.md  ← AUSTRAC, PCI-DSS, APRA CPS 234, FATF
    ├── data_model.md
    └── runbook.md
```

---

## Essential Commands

```bash
make up              # start all services (builds producer)
make down            # stop services, keep volumes
make reset           # destroy volumes + rebuild
make validate        # end-to-end health check script
make status          # service health + view row counts
make psql            # psql shell into RisingWave
make risk            # SELECT critical risk accounts
make cases           # SELECT open fraud cases
make kpis            # SELECT fraud KPIs
make fraud-rate      # current fraud_rate_pct
make logs-producer   # tail producer logs
```

### Local development (no Docker)

```bash
cd producers
pip install -e ".[dev]"                  # or: uv sync
python -m pytest tests/ -v              # run all 75 tests
ruff check . && ruff format --check .   # lint + format check
ruff format .                            # auto-format
```

---

## Development Patterns

### Adding a New Fraud Pattern

**Step 1** — Add a fraud scenario generator in `producers/generators/transaction.py`:
```python
def make_my_new_fraud(profile: CustomerProfile) -> list[TransactionEvent]:
    """One-line description of what this pattern looks like."""
    # Generate events with is_fraud=True, fraud_scenario="my_new_fraud"
    ...
```
Register it in `_FRAUD_SCENARIOS` at the bottom of that file.

**Step 2** — Add the alert mapping in `producers/generators/alert.py`:
```python
_SCENARIO_TO_ALERT_TYPE["my_new_fraud"] = "my_alert_type"
_SEVERITY_MAP["my_alert_type"] = ("high", 0.70, 0.90)
_RULE_IDS["my_alert_type"] = "RULE_007"
```

**Step 3** — Add a fraud signal dbt model in `fraud_detection/models/fraud_signals/mv_my_new_pattern.sql`:
```sql
{{ config(materialized='materialized_view') }}

SELECT
    account_id, customer_id,
    COUNT(*) AS event_count,
    window_start, window_end,
    COUNT(*) >= 3 AS is_my_pattern
FROM TUMBLE({{ ref('stg_transactions') }}, occurred_at, INTERVAL '5' MINUTE)
WHERE <filter condition>
GROUP BY account_id, customer_id, window_start, window_end
HAVING COUNT(*) >= 2
```

**Step 4** — Wire into risk score in `fraud_detection/models/risk_aggregations/mv_account_risk_score_realtime.sql` (add CTE + weight using `{{ ref('mv_my_new_pattern') }}`).

**Step 5** — Add tests in `producers/tests/` and document in `docs/fraud_patterns.md`.

### Modifying Event Schemas

All event schemas are Pydantic v2 models in `producers/models.py`. The fields `is_fraud` and `fraud_scenario` on `TransactionEvent` are marked `exclude=True` — they are **stripped from all Kafka payloads** but readable on the Python instance. Do not add any other producer-internal fields to Kafka schemas without mirroring them in the dbt source models (`fraud_detection/models/sources/`).

### dbt Model Changes

- All models target **RisingWave** (PostgreSQL-compatible) via dbt-risingwave adapter.
- Use `{{ config(materialized='materialized_view') }}` or `{{ config(materialized='source') }}` in model files.
- Reference upstream models using `{{ ref('model_name') }}` for proper dependency management.
- Time-windowed aggregations use `TUMBLE(source, time_col, INTERVAL 'N' UNIT)` — not standard SQL `WINDOW` clauses.
- Consecutive-event comparisons use `LAG()` over a partitioned stream (see `mv_geo_impossible_trips`).
- All timestamp fields arrive as `VARCHAR` in sources and are cast to `TIMESTAMPTZ` in staging.
- After any model change, run `make dbt-run` to deploy and `make psql` to test manually.

### Environment Variables

All tunable parameters live in `.env` (copy from `.env.example`):

| Variable | Default | Effect |
|---|---|---|
| `FRAUD_RATE` | `0.10` | Fraction of fraudulent transactions (0.0 = no fraud) |
| `TRANSACTION_RATE` | `20` | Transactions per second |
| `STRUCTURING_THRESHOLD` | `10000` | AML cash reporting threshold (AUD) |
| `CUSTOMER_POOL_SIZE` | `500` | Synthetic customer pool size |

**Critical invariant**: Setting `FRAUD_RATE=0.0` and restarting the producer must produce zero critical-risk accounts within 2 minutes. Tests verify this property.

---

## Testing

```bash
cd producers
python -m pytest tests/ -v
```

**Test coverage:**
- `test_models.py` — Pydantic serialisation, field exclusion guarantees
- `test_customer_pool.py` — pool size, profile structure, coord validity, uniqueness
- `test_transaction_generator.py` — all 6 fraud scenarios + `FRAUD_RATE=0` invariant
- `test_login_generator.py` — normal/failed/brute-force login
- `test_alert_generator.py` — alert type mapping, confidence ranges, DLQ for normals
- `test_kyc_generator.py` — KYC event validity, risk-tier/status correlation

All 75 tests must pass before committing. The CI pipeline (`lint` + `test` jobs) enforces this on every push.

---

## Linting & Formatting

```bash
ruff check producers/       # lint
ruff format producers/      # format
ruff check --fix producers/ # auto-fix fixable issues
```

Rules enabled: `E, W, F, I` (isort), `B` (bugbear), `C4`, `UP` (pyupgrade), `TID`, `SIM`, `RUF`. Line length: 100. Target: Python 3.11.

Pre-commit hooks run ruff, shellcheck, and standard file hygiene checks automatically on `git commit`.

```bash
pip install pre-commit && pre-commit install  # one-time setup
pre-commit run --all-files                    # run manually
```

---

## CI Pipeline

`.github/workflows/ci.yml` has 6 jobs:

| Job | Runs on | What it checks |
|---|---|---|
| `lint` | every push | ruff check + format |
| `test` | every push | pytest on Python 3.11 + 3.12 |
| `docker-build` | every push | producer image builds successfully |
| `dbt-compile` | every push | dbt compilation check for all models |
| `compose-validate` | every push | `docker compose config` is valid |
| `e2e` | PR to main only | full stack: topics populated, views non-empty, fraud cases exist |

---

## Key RisingWave Views (Quick Reference)

| View | Layer | What it answers |
|---|---|---|
| `stg_transactions` | Staging | All transactions with derived indicators |
| `mv_velocity_alerts` | Signal | Accounts with 5+ txns in 60s |
| `mv_geo_impossible_trips` | Signal | Consecutive txns >1000km apart in <2h |
| `mv_device_anomalies` | Signal | High-value CNP txns from new devices |
| `mv_cnp_spike` | Signal | Cards with 8+ CNP txns in 5min |
| `mv_login_failure_storm` | Signal | Customers with 3+ failed logins in 60s |
| `mv_structuring_detection` | Signal | Accounts with 2+ txns $9k-$9999 in 60min |
| `mv_correlated_alert_burst` | Signal | Customers with 2+ alert types in 5min |
| `mv_account_risk_score_realtime` | Risk | Per-account risk score 0.0-1.0 |
| `mv_fraud_kpis_1min` | Risk | Ops centre KPIs per 1-min window |
| `mv_open_fraud_cases` | Cases | Active high/critical cases + recommended action |

---

## Gotchas

- **RisingWave playground mode** has no persistence across container restarts. `make reset` re-runs all SQL init.
- The `risingwave-init` container exits after SQL execution — this is intentional (`service_completed_successfully`).
- Producer uses `kafka-python` (not `confluent-kafka`) — no librdkafka dependency needed in the Docker image.
- `FRAUD_RATE` controls the producer only — it does not affect the SQL detection logic. The SQL views detect fraud based on behavioural patterns regardless of the `is_fraud` flag.
