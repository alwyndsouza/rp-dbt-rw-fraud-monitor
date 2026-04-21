from __future__ import annotations

import random
from datetime import datetime, timezone

from generators.customer_pool import CustomerProfile
from models import KycProfileEvent


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


_KYC_STATUS_BY_RISK = {
    "low": ("verified", 0.95),
    "medium": ("verified", 0.80),
    "high": ("pending", 0.40),
    "pep": ("verified", 0.70),
    "sanctioned": ("failed", 0.90),
}


def generate_kyc_event(customers: list[CustomerProfile]) -> KycProfileEvent:
    profile = random.choice(customers)
    preferred_status, verified_weight = _KYC_STATUS_BY_RISK.get(
        profile.risk_tier, ("verified", 0.80)
    )

    if random.random() < verified_weight:
        kyc_status = preferred_status
    else:
        kyc_status = random.choice(["pending", "expired"])

    return KycProfileEvent(
        customer_id=profile.customer_id,
        risk_tier=profile.risk_tier,
        kyc_status=kyc_status,
        account_type=random.choices(["personal", "business", "joint"], weights=[0.75, 0.18, 0.07])[
            0
        ],
        country_of_residence=profile.home_country,
        updated_at=_now_iso(),
    )
