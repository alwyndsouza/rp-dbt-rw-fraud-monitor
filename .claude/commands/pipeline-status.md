Check the health of the running fraud detection pipeline and report a status summary.

Run the following checks in order:

1. **Service health** — `docker compose ps` — list each container and its status.

2. **Redpanda topics** — check that all 6 topics exist and have messages:
   ```bash
   docker compose exec -T redpanda rpk topic list --brokers redpanda:29092
   ```

3. **RisingWave view row counts** — query key views:
   ```bash
   docker compose exec -T risingwave psql -h localhost -p 4566 -U root -d dev -c "
     SELECT 'stg_transactions' AS view, COUNT(*) FROM stg_transactions
     UNION ALL SELECT 'mv_velocity_alerts', COUNT(*) FROM mv_velocity_alerts
     UNION ALL SELECT 'mv_geo_impossible_trips', COUNT(*) FROM mv_geo_impossible_trips
     UNION ALL SELECT 'mv_structuring_detection', COUNT(*) FROM mv_structuring_detection
     UNION ALL SELECT 'mv_account_risk_score_realtime', COUNT(*) FROM mv_account_risk_score_realtime
     UNION ALL SELECT 'mv_open_fraud_cases', COUNT(*) FROM mv_open_fraud_cases;"
   ```

4. **Current fraud KPIs**:
   ```bash
   docker compose exec -T risingwave psql -h localhost -p 4566 -U root -d dev -c "
     SELECT window_start, total_transactions, flagged_transactions, fraud_rate_pct
     FROM mv_fraud_kpis_1min ORDER BY window_start DESC LIMIT 3;"
   ```

5. **Critical risk accounts**:
   ```bash
   docker compose exec -T risingwave psql -h localhost -p 4566 -U root -d dev -c "
     SELECT COUNT(*) AS critical_accounts FROM mv_account_risk_score_realtime WHERE risk_tier = 'critical';"
   ```

Present findings as a concise table. Flag any service that is not healthy or any view that has 0 rows when it should have data (fraud signals may be 0 during warm-up — note this but do not flag as an error).

If the stack is not running, say so and suggest `make up`.
