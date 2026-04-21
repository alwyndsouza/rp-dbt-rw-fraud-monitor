Validate all SQL files for syntax and RisingWave compatibility.

Run sqlfluff on all files:
```bash
cd /home/user/fraud-detection-streaming && sqlfluff lint sql/ --dialect ansi --exclude-rules LT05,LT01,LT12,ST05,RF05,AL05 --templater raw
```

Then check for these RisingWave-specific patterns that sqlfluff won't catch:

1. **Every source definition** must use `FORMAT PLAIN ENCODE JSON` — scan `sql/01_sources.sql`.
2. **Every MV** must use `CREATE MATERIALIZED VIEW IF NOT EXISTS` — never `CREATE OR REPLACE`.
3. **Timestamp casting** — all `occurred_at` fields from sources must be cast to `TIMESTAMPTZ` in staging (check `sql/02_staging.sql`).
4. **Window functions** — aggregations over time must use `TUMBLE()` or `HOP()`, not standard SQL `WINDOW` frames (scan `sql/03_fraud_signals.sql`).
5. **LAG() usage** — confirm `mv_geo_impossible_trips` uses `LAG()` with `PARTITION BY customer_id ORDER BY occurred_at`.

Report any violations with file name and line number. If everything is clean, confirm "All SQL files are RisingWave-compatible."
