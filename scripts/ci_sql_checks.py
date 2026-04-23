"""Static SQL quality checks for CI (dbt models)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DBT_MODELS = ROOT / "fraud_detection" / "models"


def _fail(msg: str) -> None:
    print(f"[sql-check] FAIL: {msg}")
    sys.exit(1)


def _read_model(model_name: str) -> str:
    """Read a dbt model SQL file."""
    # Try fraud_signals directory first
    fraud_signals_path = DBT_MODELS / "fraud_signals" / f"{model_name}.sql"
    if fraud_signals_path.exists():
        return fraud_signals_path.read_text()

    # Try other directories
    for subdir in ["staging", "risk_aggregations", "case_management"]:
        path = DBT_MODELS / subdir / f"{model_name}.sql"
        if path.exists():
            return path.read_text()

    _fail(f"could not find model: {model_name}")
    return ""


def main() -> None:
    checks = [
        ("mv_velocity_alerts", r"COUNT\(\*\)\s*>?=\s*5", "velocity threshold must be >=5"),
        ("mv_cnp_spike", r"COUNT\(\*\)\s*>?=\s*8", "cnp spike threshold must be >=8"),
        (
            "mv_login_failure_storm",
            r"COUNT\(\*\)\s*>?=\s*3",
            "login failure threshold must be >=3",
        ),
    ]

    for model_name, threshold_pattern, message in checks:
        sql = _read_model(model_name)
        if not re.search(threshold_pattern, sql):
            _fail(f"{message} in {model_name}")

    # Check device anomaly anti-join
    device_sql = _read_model("mv_device_anomalies")
    if "historical_known_devices" not in device_sql or "WHERE d.device_id IS NULL" not in device_sql:
        _fail("device anomaly view must anti-join against known devices")

    print("[sql-check] PASS: SQL guardrails validated")


if __name__ == "__main__":
    main()
