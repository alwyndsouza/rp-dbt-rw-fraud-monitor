# Contributing Guide

Thanks for contributing to `fraud-detection-streaming`.

## 1) Engineering Standards

### Python
- Target Python 3.11.
- Run `ruff check producers` before opening a PR.
- Prefer small, testable functions and deterministic behavior where practical.
- Keep generator payloads schema-compatible with SQL sources.

### dbt Models (RisingWave)
- Keep pipeline layered:
  1. `models/sources/` - Kafka sources
  2. `models/staging/` - Type casting and enrichment
  3. `models/fraud_signals/` - Detection logic
  4. `models/risk_aggregations/` - Risk scores and KPIs
  5. `models/case_management/` - Analyst workflows
- Use `{{ ref('model_name') }}` for dependencies between models.
- Use `{{ config(materialized='materialized_view') }}` for most models.
- Avoid breaking downstream model contracts without coordinated updates.
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
make dbt-test
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
- [ ] dbt models and joins preserve intended semantics.
- [ ] Model dependencies are correctly specified using `{{ ref() }}`.
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
- [ ] dbt tests defined for data quality guardrails.
- [ ] dbt model documentation added where appropriate.
- [ ] README/docs updated when behavior or operations change.
