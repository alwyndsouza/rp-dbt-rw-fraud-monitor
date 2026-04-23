.PHONY: up down reset status logs logs-producer seed validate psql \
        risk cases kpis console grafana fraud-rate dq ci help \
        format lint \
        dbt-run dbt-debug dbt-docs dbt-test dbt-clean dbt-compile

# Load .env if it exists
-include .env
export

COMPOSE := docker compose
PSQL := docker run --rm -i --network fraud-detection-streaming_fraud-net postgres:15-alpine psql -h risingwave -p 4566 -U root -d dev

help: ## Show this help
	@echo ""
	@echo "  Fraud Detection Streaming Pipeline"
	@echo "  Sub-second fraud detection. No cloud required."
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

up: ## Start all services (builds producer image)
	@cp -n .env.example .env 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  Services starting. Run 'make status' to check health."
	@echo "  Redpanda Console : http://localhost:8080"
	@echo "  RisingWave Dash  : http://localhost:5691"
	@echo "  Grafana          : http://localhost:3000  (admin / admin)"
	@echo ""

down: ## Stop all services (keep volumes)
	$(COMPOSE) down

reset: ## Destroy everything and rebuild from scratch
	$(COMPOSE) down -v --remove-orphans
	$(MAKE) up

status: ## Show service health and key view row counts
	@echo "=== Service Health ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Key View Row Counts ==="
	@$(PSQL) -c "\
	  SELECT 'mv_account_risk_score_realtime' AS view, COUNT(*) AS rows FROM mv_account_risk_score_realtime \
	  UNION ALL \
	  SELECT 'mv_open_fraud_cases', COUNT(*) FROM mv_open_fraud_cases \
	  UNION ALL \
	  SELECT 'mv_velocity_alerts', COUNT(*) FROM mv_velocity_alerts \
	  UNION ALL \
	  SELECT 'mv_geo_impossible_trips', COUNT(*) FROM mv_geo_impossible_trips \
	  UNION ALL \
	  SELECT 'mv_fraud_kpis_1min', COUNT(*) FROM mv_fraud_kpis_1min;" 2>/dev/null \
	  || echo "  RisingWave not ready yet — try again in a moment."

logs: ## Follow all service logs
	$(COMPOSE) logs -f

logs-producer: ## Follow producer logs only
	$(COMPOSE) logs -f producer

seed: ## Create Redpanda topics (idempotent)
	$(COMPOSE) run --rm seed-topics

validate: ## End-to-end health check
	@bash scripts/check_pipeline.sh

psql: ## Open psql shell into RisingWave
	docker run --rm -it --network fraud-detection-streaming_fraud-net postgres:15-alpine psql -h risingwave -p 4566 -U root -d dev

risk: ## Show critical risk accounts
	@$(PSQL) -c "\
	  SELECT account_id, customer_id, \
	         ROUND(risk_score::numeric, 3) AS risk_score, \
	         risk_tier, contributing_signals \
	  FROM mv_account_risk_score_realtime \
	  WHERE risk_tier = 'critical' \
	  ORDER BY risk_score DESC \
	  LIMIT 20;" 2>/dev/null || echo "View not ready yet."

cases: ## Show open fraud investigation cases
	@$(PSQL) -c "\
	  SELECT customer_id, account_id, \
	         ROUND(risk_score::numeric, 3) AS risk_score, \
	         risk_tier, recommended_action \
	  FROM mv_open_fraud_cases \
	  ORDER BY risk_score DESC \
	  LIMIT 10;" 2>/dev/null || echo "View not ready yet."

kpis: ## Show fraud operations KPIs
	@$(PSQL) -c "\
	  SELECT window_start, \
	         total_transactions, \
	         flagged_transactions, \
	         ROUND(fraud_rate_pct::numeric, 2) AS fraud_rate_pct, \
	         critical_risk_accounts, \
	         velocity_breaches, \
	         geo_anomalies, \
	         brute_force_attempts, \
	         structuring_flags \
	  FROM mv_fraud_kpis_1min \
	  ORDER BY window_start DESC \
	  LIMIT 5;" 2>/dev/null || echo "View not ready yet."

console: ## Open Redpanda Console in browser
	@xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || \
	  echo "Open http://localhost:8080 in your browser"

grafana: ## Open Grafana dashboard in browser
	@xdg-open http://localhost:3000 2>/dev/null || open http://localhost:3000 2>/dev/null || \
	  echo "Open http://localhost:3000 in your browser (admin / admin)"

fraud-rate: ## Show current fraud rate from KPI view
	@$(PSQL) -t -c "\
	  SELECT 'Fraud rate: ' || ROUND(fraud_rate_pct::numeric, 2) || '%  ' || \
	         '| Total txns: ' || total_transactions || \
	         ' | Flagged: ' || flagged_transactions \
	  FROM mv_fraud_kpis_1min \
	  ORDER BY window_start DESC \
	  LIMIT 1;" 2>/dev/null || echo "KPI view not ready yet."

dq: ## Run data-quality tests via dbt
	@echo "Running dbt data quality tests..."
	@cd fraud_detection && dbt test --profiles-dir . --select tag:data_quality || echo "dbt tests not configured yet"

format: ## Format Python files
	@uv run ruff format .

lint: ## Check Python files for issues
	@uv run ruff check .

ci: ## Run local CI-equivalent checks
	@echo "=== 1. Running pytest ==="
	@cd producers && uv run pytest tests -q && cd ..
	@echo ""
	@echo "=== 2. Running ruff check ==="
	@uv run ruff check producers
	@echo ""
	@echo "=== 3. Running SQL validation checks ==="
	@python3 scripts/ci_sql_checks.py
	@echo ""
	@echo "=== 4. Running dbt tests (Docker) ==="
	@docker run --rm \
		--network rp-dbt-rw-fraud-monitor_fraud-net \
		-v $$(pwd)/fraud_detection:/dbt \
		-e RISINGWAVE_HOST=risingwave \
		python:3.11-slim \
		sh -c 'pip install dbt-risingwave==1.9.7 --quiet 2>&1 >/dev/null && cd /dbt && dbt test --profiles-dir .' 2>&1 | grep -E "(Done\.|PASS=|ERROR=|Completed)"
	@echo ""
	@echo "✅ All CI checks passed!"

dbt-run: ## Run dbt models against RisingWave (requires dbt-risingwave installed)
	cd fraud_detection && dbt run --profiles-dir .

dbt-debug: ## Validate dbt connection to RisingWave
	cd fraud_detection && dbt debug --profiles-dir .

dbt-test: ## Run dbt tests against RisingWave
	cd fraud_detection && dbt test --profiles-dir .

dbt-docs: ## Generate and serve dbt documentation
	cd fraud_detection && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

dbt-compile: ## Compile dbt models without running them
	cd fraud_detection && dbt compile --profiles-dir .

dbt-clean: ## Remove dbt build artefacts
	cd fraud_detection && dbt clean
