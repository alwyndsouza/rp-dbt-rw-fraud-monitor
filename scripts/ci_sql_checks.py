"""Static SQL quality checks for CI."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNALS_SQL = ROOT / "sql" / "03_fraud_signals.sql"


def _fail(msg: str) -> None:
    print(f"[sql-check] FAIL: {msg}")
    sys.exit(1)


def _extract_block(sql: str, view_name: str) -> str:
    pattern = re.compile(
        rf"CREATE MATERIALIZED VIEW IF NOT EXISTS\s+{view_name}\s+AS(.*?);\n",
        re.S,
    )
    match = pattern.search(sql)
    if not match:
        _fail(f"could not locate view block: {view_name}")
    return match.group(1)


def main() -> None:
    sql = SIGNALS_SQL.read_text()

    checks = [
        ("mv_velocity_alerts", r"COUNT\(\*\)\s*>?=\s*5", "velocity threshold must be >=5"),
        ("mv_cnp_spike", r"COUNT\(\*\)\s*>?=\s*8", "cnp spike threshold must be >=8"),
        (
            "mv_login_failure_storm",
            r"COUNT\(\*\)\s*>?=\s*3",
            "login failure threshold must be >=3",
        ),
    ]

    for view_name, threshold_pattern, message in checks:
        block = _extract_block(sql, view_name)
        if not re.search(threshold_pattern, block):
            _fail(f"{message} in {view_name}")

    if "historical_known_devices" not in sql or "WHERE d.device_id IS NULL" not in sql:
        _fail("device anomaly view must anti-join against historical known devices")

    print("[sql-check] PASS: SQL guardrails validated")


if __name__ == "__main__":
    main()
