#!/usr/bin/env bash
# Post-edit hook: lint/format Python files, validate SQL files, check YAML.
# Called by Claude Code after every Edit or Write tool use.
# Usage: post-edit.sh <file_path>

FILE="${1:-}"
[ -z "$FILE" ] && exit 0

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "/home/user/fraud-detection-streaming")"

# ── Python: ruff check + format ────────────────────────────────────────────
if [[ "$FILE" == *.py ]]; then
  if command -v ruff &>/dev/null; then
    echo "[hook] ruff check $FILE"
    ruff check --fix --quiet "$FILE" 2>&1 && ruff format --quiet "$FILE" 2>&1
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
      echo "[hook] ⚠ ruff found unfixable issues in $FILE — run: ruff check $FILE"
    fi
  fi
fi

# ── SQL: sqlfluff lint ─────────────────────────────────────────────────────
if [[ "$FILE" == *.sql ]]; then
  if command -v sqlfluff &>/dev/null; then
    echo "[hook] sqlfluff lint $FILE"
    sqlfluff lint "$FILE" \
      --dialect ansi \
      --exclude-rules LT05,LT01,LT12,ST05,RF05,AL05 \
      --templater raw \
      --quiet 2>&1 || echo "[hook] ⚠ sqlfluff found issues in $FILE — run: sqlfluff lint $FILE"
  fi
fi

# ── YAML: check syntax ─────────────────────────────────────────────────────
if [[ "$FILE" == *.yml || "$FILE" == *.yaml ]]; then
  if command -v python3 &>/dev/null; then
    python3 -c "import sys, yaml; yaml.safe_load(open('$FILE'))" 2>&1 \
      && echo "[hook] ✓ YAML syntax OK: $FILE" \
      || echo "[hook] ✗ YAML syntax error in $FILE"
  fi
fi

# ── docker-compose.yml: validate config ───────────────────────────────────
if [[ "$FILE" == *docker-compose* ]]; then
  if command -v docker &>/dev/null; then
    echo "[hook] docker compose config check"
    docker compose -f "$REPO_ROOT/docker-compose.yml" config --quiet 2>&1 \
      && echo "[hook] ✓ docker-compose.yml is valid" \
      || echo "[hook] ✗ docker-compose.yml has errors"
  fi
fi

exit 0
