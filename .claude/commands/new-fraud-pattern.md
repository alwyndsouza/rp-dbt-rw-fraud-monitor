Scaffold a new fraud detection pattern end-to-end. Ask the user for:
1. Pattern name (snake_case, e.g. `card_testing`)
2. Brief description of the real-world fraud behaviour
3. Which event stream(s) it uses (transactions / logins / alerts)
4. The detection condition (e.g. "5+ small transactions within 2 minutes")
5. Suggested risk score weight (0.10–0.40)

Then generate ALL of the following, following existing code style exactly:

**producers/generators/transaction.py** — add `make_<pattern_name>()` function returning `list[TransactionEvent]` with `is_fraud=True, fraud_scenario="<pattern_name>"`.

**producers/generators/alert.py** — add entries to `_SCENARIO_TO_ALERT_TYPE`, `_SEVERITY_MAP`, and `_RULE_IDS`.

**sql/03_fraud_signals.sql** — add `mv_<pattern_name>` materialized view using `TUMBLE()` or `LAG()` as appropriate.

**sql/04_risk_aggregations.sql** — add a CTE in `mv_account_risk_score_realtime` and wire in the weight.

**producers/tests/test_transaction_generator.py** — add a `TestMyNewPattern` class with at minimum: `test_is_fraud`, `test_fraud_scenario_name`, `test_amounts_in_expected_range`, `test_same_account`.

**docs/fraud_patterns.md** — add a new section following the existing template (real-world description, detection logic, signal latency, false positive risk, regulatory reference).

After generating, run `/test` to confirm all tests still pass.
