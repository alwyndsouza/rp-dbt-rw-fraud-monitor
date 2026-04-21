"""Tests for KYC profile event generator."""

import random

import pytest

from generators.customer_pool import build_customer_pool
from generators.kyc_profile import generate_kyc_event


@pytest.fixture(scope="module")
def customers():
    random.seed(30)
    return build_customer_pool(50)


def test_generates_valid_event(customers):
    evt = generate_kyc_event(customers)
    assert evt.customer_id
    assert evt.risk_tier in {"low", "medium", "high", "pep", "sanctioned"}
    assert evt.kyc_status in {"verified", "pending", "failed", "expired"}
    assert evt.account_type in {"personal", "business", "joint"}
    assert evt.country_of_residence
    assert evt.updated_at.endswith("Z")


def test_customer_id_from_pool(customers):
    pool_ids = {c.customer_id for c in customers}
    for _ in range(20):
        evt = generate_kyc_event(customers)
        assert evt.customer_id in pool_ids


def test_high_risk_tier_is_not_always_verified():
    random.seed(42)
    high_risk = build_customer_pool(50)
    for c in high_risk:
        object.__setattr__(c, "risk_tier", "high")
    statuses = [generate_kyc_event([c]).kyc_status for c in high_risk]
    assert "pending" in statuses or "expired" in statuses, (
        "High-risk customers should sometimes have non-verified KYC"
    )
