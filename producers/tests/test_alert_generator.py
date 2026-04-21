"""Tests for alert event generators."""

import random

import pytest

from generators.alert import make_alert_for_transaction, make_noise_alert
from generators.customer_pool import build_customer_pool
from generators.transaction import (
    make_account_takeover_transaction,
    make_geo_impossible_transaction,
    make_normal_transaction,
    make_structuring_transactions,
    make_unusual_mcc_transaction,
    make_velocity_fraud,
)


@pytest.fixture(scope="module")
def customers():
    random.seed(20)
    return build_customer_pool(10)


@pytest.fixture(scope="module")
def profile(customers):
    return customers[0]


class TestMakeAlertForTransaction:
    def test_no_alert_for_normal_transaction(self, profile):
        txn = make_normal_transaction(profile)
        alert = make_alert_for_transaction(txn)
        assert alert is None

    @pytest.mark.parametrize(
        "make_fn,expected_type",
        [
            (make_velocity_fraud, "velocity"),
            (make_geo_impossible_transaction, "geo_anomaly"),
            (make_account_takeover_transaction, "account_takeover"),
            (make_unusual_mcc_transaction, "device_fingerprint"),
        ],
    )
    def test_correct_alert_type(self, profile, make_fn, expected_type, monkeypatch):
        # Skip the artificial delay in tests
        import time

        monkeypatch.setattr(time, "sleep", lambda _: None)

        txns = make_fn(profile)
        txn = txns[0] if isinstance(txns, list) else txns
        alert = make_alert_for_transaction(txn)
        assert alert is not None
        assert alert.alert_type == expected_type

    def test_structuring_alert_type(self, profile, monkeypatch):
        import time

        monkeypatch.setattr(time, "sleep", lambda _: None)

        txn = make_structuring_transactions(profile, 10000.0)[0]
        alert = make_alert_for_transaction(txn)
        assert alert is not None
        assert alert.alert_type == "structuring"

    def test_high_fraud_confidence(self, profile, monkeypatch):
        import time

        monkeypatch.setattr(time, "sleep", lambda _: None)

        txn = make_geo_impossible_transaction(profile)
        alert = make_alert_for_transaction(txn)
        assert alert.confidence_score >= 0.75

    def test_alert_references_transaction(self, profile, monkeypatch):
        import time

        monkeypatch.setattr(time, "sleep", lambda _: None)

        txn = make_velocity_fraud(profile)[0]
        alert = make_alert_for_transaction(txn)
        assert alert.transaction_id == txn.transaction_id
        assert alert.customer_id == txn.customer_id


class TestMakeNoiseAlert:
    def test_low_severity(self, customers):
        for _ in range(20):
            alert = make_noise_alert(customers)
            assert alert.severity == "low"

    def test_low_confidence(self, customers):
        for _ in range(20):
            alert = make_noise_alert(customers)
            assert 0.10 <= alert.confidence_score <= 0.40

    def test_rule_id_is_noise(self, customers):
        for _ in range(10):
            assert make_noise_alert(customers).rule_id == "RULE_099"
