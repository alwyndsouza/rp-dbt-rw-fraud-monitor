#!/usr/bin/env bash
# Pre-bash hook: warn before destructive operations.
# Exits non-zero to block the command if it matches a destructive pattern.
# Claude Code will surface the message to the user before proceeding.

COMMAND="${1:-}"

# Patterns that warrant an explicit warning (non-blocking — just logs)
WARN_PATTERNS=(
  "docker compose down -v"
  "make reset"
  "DROP TABLE"
  "DROP SOURCE"
  "DROP MATERIALIZED VIEW"
  "git push --force"
  "git push -f"
  "git reset --hard"
)

for pattern in "${WARN_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qi "$pattern"; then
    echo "[hook] ⚠ DESTRUCTIVE OPERATION DETECTED: '$pattern'"
    echo "[hook]   Command: $COMMAND"
    echo "[hook]   This will destroy data or state that cannot be recovered automatically."
    echo "[hook]   If this is intentional, confirm before proceeding."
    # Return 2 to surface warning but not hard-block (Claude Code shows it as a notice)
    exit 2
  fi
done

exit 0
