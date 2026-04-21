# Troubleshooting Guide

## 1) Stack does not fully start

### Symptoms
- `make status` shows containers restarting or exited.

### Checks
```bash
docker compose ps
docker compose logs --tail=200 redpanda risingwave risingwave-init producer
```

### Typical fixes
- Reset corrupted local state:
  ```bash
  make reset
  ```
- Ensure ports 3000, 4566, 5691, 8080, 9092 are not occupied.

---

## 2) RisingWave views are empty

### Symptoms
- `make risk` / `make kpis` returns 0 rows.

### Checks
```bash
make logs-producer
make psql
-- in psql
SELECT COUNT(*) FROM stg_transactions;
SELECT COUNT(*) FROM mv_velocity_alerts;
```

### Typical fixes
- Wait 60–120 seconds for first tumbling windows to complete.
- Verify `risingwave-init` executed SQL successfully.
- Verify producer is connected to `REDPANDA_BROKERS`.

---

## 3) Producer health endpoint returns degraded (503)

### Symptoms
- `curl http://localhost:8001/health` returns `status=degraded`.

### Cause
- No publishes observed recently (`stale_seconds` high).

### Fixes
- Inspect producer logs:
  ```bash
  make logs-producer
  ```
- Restart producer:
  ```bash
  docker compose restart producer
  ```
- Confirm broker reachability from container env/logs.

---

## 4) Grafana dashboard has no data

### Checks
```bash
curl -sSf http://localhost:3000/api/health
make psql
-- in psql
SELECT COUNT(*) FROM mv_fraud_kpis_1min;
```

### Typical fixes
- Ensure RisingWave is healthy before Grafana starts.
- Confirm datasource provisioning in `grafana/provisioning/datasources/risingwave.yml`.
- Recreate Grafana volume if provisioning got stale:
  ```bash
  docker compose down -v
  make up
  ```

---

## 5) Validation script fails intermittently

### Reason
- Pipeline warm-up race: first minute windows are not yet populated.

### Fix
- Re-run after 1–2 minutes:
```bash
make validate
```

---

## 6) Performance or memory pressure on laptop

### Mitigations
- Reduce synthetic load in `.env`:
  - `TRANSACTION_RATE`
  - `LOGIN_RATE`
  - `CUSTOMER_POOL_SIZE`
- Lower broker memory allocation in compose command.
- Disable minute tick in constrained environments:
  - `MINUTE_TICK_ENABLED=false`

