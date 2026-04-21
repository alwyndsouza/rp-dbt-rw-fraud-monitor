from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from generators.customer_pool import CustomerProfile
from models import CardEvent


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


_NORMAL_EVENTS = ["limit_change", "pin_change", "reissue"]
_FRAUD_EVENTS = ["block", "reissue"]


def make_card_event(
    profile: CustomerProfile,
    fraud_triggered: bool = False,
) -> CardEvent:
    account_idx = random.randrange(len(profile.account_ids))

    if fraud_triggered:
        event_type = random.choice(_FRAUD_EVENTS)
        initiated_by = "fraud_system"
    else:
        event_type = random.choice(_NORMAL_EVENTS)
        initiated_by = random.choices(["customer", "bank"], weights=[0.7, 0.3])[0]

    return CardEvent(
        event_id=str(uuid.uuid4()),
        account_id=profile.account_ids[account_idx],
        customer_id=profile.customer_id,
        card_last4=profile.card_last4s[account_idx],
        event_type=event_type,
        initiated_by=initiated_by,
        occurred_at=_now_iso(),
    )


def generate_card_event(
    customers: list[CustomerProfile],
    fraud_rate: float,
) -> CardEvent:
    profile = random.choice(customers)
    fraud_triggered = random.random() < fraud_rate * 0.3
    return make_card_event(profile, fraud_triggered)
