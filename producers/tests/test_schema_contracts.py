"""Contract tests ensuring producer schemas align with RisingWave source definitions."""

from __future__ import annotations

import re
from pathlib import Path

from models import AlertEvent, CardEvent, KycProfileEvent, LoginEvent, TransactionEvent

ROOT = Path(__file__).resolve().parents[2]
DBT_SOURCES = ROOT / "fraud_detection" / "models" / "sources"


def _extract_source_columns(sql: str) -> list[str]:
    """Extract column names from a dbt source model."""
    pattern = re.compile(
        r"CREATE SOURCE IF NOT EXISTS.*?\((.*?)\)\s*WITH\s*\(",
        re.S,
    )
    match = pattern.search(sql)
    assert match is not None, "Source definition not found in dbt model"
    block = match.group(1)
    columns = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        # Extract just the column name (first token)
        columns.append(line.split()[0])
    return columns


def _read_dbt_source(source_name: str) -> str:
    """Read a dbt source model SQL file."""
    source_file = DBT_SOURCES / f"{source_name}.sql"
    return source_file.read_text()


def _model_fields(model) -> list[str]:
    return list(model.model_fields.keys())


def test_transaction_schema_contract():
    sql = _read_dbt_source("transactions")
    source_cols = _extract_source_columns(sql)
    model_cols = [
        c for c in _model_fields(TransactionEvent) if c not in {"is_fraud", "fraud_scenario"}
    ]
    assert source_cols == model_cols


def test_login_schema_contract():
    sql = _read_dbt_source("login_events")
    source_cols = _extract_source_columns(sql)
    assert source_cols == _model_fields(LoginEvent)


def test_card_schema_contract():
    sql = _read_dbt_source("card_events")
    source_cols = _extract_source_columns(sql)
    assert source_cols == _model_fields(CardEvent)


def test_alert_schema_contract():
    sql = _read_dbt_source("alert_events")
    source_cols = _extract_source_columns(sql)
    assert source_cols == _model_fields(AlertEvent)


def test_kyc_schema_contract():
    sql = _read_dbt_source("kyc_profile_events")
    source_cols = _extract_source_columns(sql)
    assert source_cols == _model_fields(KycProfileEvent)
