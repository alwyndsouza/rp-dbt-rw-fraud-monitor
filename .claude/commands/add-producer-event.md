Scaffold a new event type end-to-end (Pydantic model → Kafka topic → RisingWave source → staging MV).

Ask the user for:
1. Event name (snake_case, e.g. `device_fingerprint_event`)
2. Fields with types (e.g. `fingerprint_id: str`, `risk_score: float`)
3. Kafka topic name
4. Publish rate (events per second)

Then generate:

**producers/models.py** — add a new Pydantic `BaseModel` class following the existing style. Use `str | None` for optional fields (not `Optional[str]`).

**producers/generators/<event_name>.py** — add a generator module with a `generate_<event_name>()` function. Follow the pattern in `generators/kyc_profile.py`.

**producers/main.py** — add a `run_<event_name>_producer()` thread function and register it in `main()`.

**producers/config.py** — add a `<EVENT_NAME>_RATE` env var with sensible default.

**docker-compose.yml** — add the new rate env var to the `producer` service environment block.

**.env.example** — document the new env var.

**sql/01_sources.sql** — add `CREATE SOURCE IF NOT EXISTS <topic_name>` with all fields.

**sql/02_staging.sql** — add `CREATE MATERIALIZED VIEW IF NOT EXISTS stg_<event_name>` with type casting.

**producers/tests/test_<event_name>_generator.py** — add basic tests: valid event structure, required fields present, timestamps are ISO-8601.

After scaffolding, run `/test` and `/lint` to confirm everything is clean.
