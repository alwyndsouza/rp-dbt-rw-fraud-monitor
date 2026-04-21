# Contributing Guide

Thanks for contributing to `fraud-detection-streaming`.

## 1) Engineering Standards

### Python
- Target Python 3.11.
- Run `ruff check producers` before opening a PR.
- Prefer small, testable functions and deterministic behavior where practical.
- Keep generator payloads schema-compatible with SQL sources.

### SQL (RisingWave)
- Keep pipeline layered:
  1. `01_sources.sql`
  2. `02_staging.sql`
  3. `03_fraud_signals.sql`
  4. `04_risk_aggregations.sql`
  5. `05_case_management.sql`
- Avoid breaking downstream MV contracts without coordinated updates.
- Document non-obvious thresholds and window choices inline.

### Infrastructure / Compose
- Prefer explicit versions over floating tags for production use.
- Preserve health checks and startup ordering.
- Keep changes idempotent (`seed-topics`, SQL init).

---

## 2) Local Development

```bash
make up
make validate
make dq
pytest producers/tests -q
ruff check producers
```

Useful:
```bash
make status
make logs-producer
make psql
```

---

## 3) Branching Strategy

- `main`: stable integration branch.
- Feature branches: `feat/<area>-<short-description>`
- Fix branches: `fix/<area>-<short-description>`
- Docs branches: `docs/<area>-<short-description>`

Rebase on latest `main` before merge when possible.

---

## 4) Pull Request Guidelines

Each PR should include:
- Clear summary of behavior changes
- Risk assessment (what can break)
- Validation evidence (test output, `make validate`, or SQL checks)
- Rollback plan for operationally significant changes
- CI status green (`.github/workflows/ci.yml`)

If dashboards or user-visible flows changed, include screenshots.

---

## 5) Code Review Checklist

Reviewers should verify:

### Correctness
- [ ] Behavior matches requirement and is backward-compatible or clearly documented.
- [ ] SQL views and joins preserve intended semantics.
- [ ] Event schema fields and types remain consistent end-to-end.

### Reliability
- [ ] Errors are logged with actionable context.
- [ ] Retry/backoff behavior is safe.
- [ ] Health checks still reflect real service readiness.

### Security
- [ ] No credentials or secrets in code/docs.
- [ ] No unsafe default exposure added (ports, unauthenticated admin APIs).
- [ ] Sensitive data handling is appropriate for simulation scope.

### Performance & Scale
- [ ] New windows/joins are bounded and justified.
- [ ] High-cardinality operations are minimized.
- [ ] Producer thread behavior does not introduce unbounded growth.

### Testing & Documentation
- [ ] Tests cover new logic and edge cases.
- [ ] Data quality guardrails remain valid (`sql/99_data_quality_checks.sql`, schema contracts).
- [ ] README/docs updated when behavior or operations change.
