"""Contract tests ensuring producer schemas align with RisingWave source definitions."""

from __future__ import annotations

import re
from pathlib import Path

from models import AlertEvent, CardEvent, KycProfileEvent, LoginEvent, TransactionEvent

ROOT = Path(__file__).resolve().parents[2]
SOURCES_SQL = ROOT / "sql" / "01_sources.sql"


def _extract_source_columns(sql: str, source_name: str) -> list[str]:
    pattern = re.compile(
        rf"CREATE SOURCE IF NOT EXISTS\s+{source_name}\s*\((.*?)\)\s*WITH\s*\(",
        re.S,
    )
    match = pattern.search(sql)
    assert match is not None, f"Source {source_name} not found in 01_sources.sql"
    block = match.group(1)
    columns = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        columns.append(line.split()[0])
    return columns


def _model_fields(model) -> list[str]:
    return list(model.model_fields.keys())


def test_transaction_schema_contract():
    sql = SOURCES_SQL.read_text()
    source_cols = _extract_source_columns(sql, "transactions")
    model_cols = [
        c for c in _model_fields(TransactionEvent) if c not in {"is_fraud", "fraud_scenario"}
    ]
    assert source_cols == model_cols


def test_login_schema_contract():
    sql = SOURCES_SQL.read_text()
    source_cols = _extract_source_columns(sql, "login_events")
    assert source_cols == _model_fields(LoginEvent)


def test_card_schema_contract():
    sql = SOURCES_SQL.read_text()
    source_cols = _extract_source_columns(sql, "card_events")
    assert source_cols == _model_fields(CardEvent)


def test_alert_schema_contract():
    sql = SOURCES_SQL.read_text()
    source_cols = _extract_source_columns(sql, "alert_events")
    assert source_cols == _model_fields(AlertEvent)


def test_kyc_schema_contract():
    sql = SOURCES_SQL.read_text()
    source_cols = _extract_source_columns(sql, "kyc_profile_events")
    assert source_cols == _model_fields(KycProfileEvent)
