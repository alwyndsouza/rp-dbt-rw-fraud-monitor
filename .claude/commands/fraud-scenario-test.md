Run a targeted fraud scenario simulation and verify the end-to-end detection chain.

Ask the user which scenario to test:
- `velocity` — 6+ small CNP transactions from one account in 60 seconds
- `geo_impossible` — transaction >1000km from previous transaction within 2 hours  
- `account_takeover` — new device + high-value CNP transaction
- `cnp_spike` — 10+ CNP transactions in 5 minutes
- `structuring` — 2+ transactions $9,000-$9,999 within 60 minutes
- `brute_force` — 3+ failed logins in 60 seconds
- `compound` — 2+ alert types on same customer in 5 minutes

For the chosen scenario:

1. Show the generator code from `producers/generators/transaction.py` (or `login.py`).
2. Show the detection SQL from `sql/03_fraud_signals.sql`.
3. Show how it contributes to the risk score in `sql/04_risk_aggregations.sql`.
4. Run the unit tests for that scenario:
   ```bash
   cd /home/user/fraud-detection-streaming/producers && python -m pytest tests/ -v -k "<scenario>"
   ```
5. Explain the end-to-end detection chain: producer event → Redpanda topic → RisingWave source → staging MV → signal MV → risk score → open case.
6. State the expected signal latency and the risk score contribution.
