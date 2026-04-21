Audit the current risk score model and produce a structured report.

1. Read `sql/04_risk_aggregations.sql` — extract the full list of signals, their weights, and lookback windows from `mv_account_risk_score_realtime`.

2. Read `sql/03_fraud_signals.sql` — for each signal CTE referenced in the risk score, verify:
   - The source MV exists
   - The lookback window matches the documentation in `CLAUDE.md`
   - The flag condition (`= 1`) is logically sound

3. Check the risk tier thresholds (low/medium/high/critical) are consistent between `mv_account_risk_score_realtime` and `mv_open_fraud_cases`.

4. Check the `recommended_action` logic in `mv_open_fraud_cases` — confirm the score thresholds and signal conditions match the documentation in `README.md` and `docs/fraud_patterns.md`.

5. Identify any signals that can exceed 1.0 when combined (i.e. weights sum > 0.9 without triggering `LEAST(1.0, ...)`).

6. Produce a table:

| Signal | Weight | Lookback | Source MV | Status |
|---|---|---|---|---|
| velocity | +0.25 | 10min | mv_velocity_alerts | ✓ |
| ... | | | | |

Flag any inconsistencies as `⚠ MISMATCH`.
