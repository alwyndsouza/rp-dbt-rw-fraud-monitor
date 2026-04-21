Explain a RisingWave materialized view in plain English suitable for a risk engineer unfamiliar with stream processing.

The user will provide a view name (e.g. `mv_velocity_alerts` or `mv_account_risk_score_realtime`).

For the requested view:

1. Read the SQL definition from the appropriate file in `sql/`.
2. Explain in 3-5 sentences: what fraud pattern it detects, which source data it reads, what the key filter/window condition is, and what the output rows represent.
3. Show the lineage: which upstream views/sources feed into it, and which downstream views consume it (reference `CLAUDE.md` lineage table).
4. Give a concrete example row: what would a real output record look like with realistic values?
5. Note the signal latency (how quickly after a fraud event does this view update?).
6. State the false positive risk (low/medium/high) and the main mitigation.

Keep the explanation jargon-free. A product manager should be able to understand it.
