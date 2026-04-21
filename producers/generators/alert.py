from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timezone

from models import AlertEvent, TransactionEvent

_SCENARIO_TO_ALERT_TYPE = {
    "velocity": "velocity",
    "geo_impossible": "geo_anomaly",
    "account_takeover": "account_takeover",
    "cnp_spike": "card_not_present",
    "unusual_mcc": "device_fingerprint",
    "structuring": "structuring",
}

_SEVERITY_MAP = {
    "velocity": ("high", 0.75, 0.92),
    "geo_anomaly": ("critical", 0.85, 0.99),
    "account_takeover": ("critical", 0.88, 0.99),
    "card_not_present": ("high", 0.75, 0.93),
    "device_fingerprint": ("medium", 0.60, 0.82),
    "structuring": ("critical", 0.80, 0.97),
}

_RULE_IDS = {
    "velocity": "RULE_001",
    "geo_anomaly": "RULE_002",
    "account_takeover": "RULE_003",
    "card_not_present": "RULE_004",
    "device_fingerprint": "RULE_005",
    "structuring": "RULE_006",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def make_alert_for_transaction(txn: TransactionEvent) -> AlertEvent | None:
    """Reactively create an alert for a flagged transaction (after artificial delay)."""
    scenario = txn.fraud_scenario
    if not scenario:
        return None

    alert_type = _SCENARIO_TO_ALERT_TYPE.get(scenario)
    if alert_type is None:
        return None

    severity_label, conf_min, conf_max = _SEVERITY_MAP.get(alert_type, ("medium", 0.50, 0.75))

    # Artificial rule-engine latency: 100-800ms
    time.sleep(random.uniform(0.1, 0.8))

    return AlertEvent(
        alert_id=str(uuid.uuid4()),
        customer_id=txn.customer_id,
        transaction_id=txn.transaction_id,
        alert_type=alert_type,
        severity=severity_label,
        confidence_score=round(random.uniform(conf_min, conf_max), 4),
        rule_id=_RULE_IDS.get(alert_type, "RULE_099"),
        occurred_at=_now_iso(),
    )


def make_noise_alert(customers_sample: list) -> AlertEvent:
    """Low-confidence noise alert (false positive simulation)."""
    customer = random.choice(customers_sample)
    alert_type = random.choice(list(_SCENARIO_TO_ALERT_TYPE.values()))
    return AlertEvent(
        alert_id=str(uuid.uuid4()),
        customer_id=customer.customer_id,
        transaction_id=str(uuid.uuid4()),
        alert_type=alert_type,
        severity="low",
        confidence_score=round(random.uniform(0.10, 0.40), 4),
        rule_id="RULE_099",
        occurred_at=_now_iso(),
    )
