"""Tests for transaction event generators — normal and all 6 fraud scenarios."""

import random
from datetime import datetime

import pytest

from generators.customer_pool import build_customer_pool
from generators.transaction import (
    generate_transaction_batch,
    make_account_takeover_transaction,
    make_cnp_spike_transactions,
    make_geo_impossible_transaction,
    make_normal_transaction,
    make_structuring_transactions,
    make_unusual_mcc_transaction,
    make_velocity_fraud,
)


@pytest.fixture(scope="module")
def customers():
    random.seed(0)
    return build_customer_pool(20)


@pytest.fixture(scope="module")
def profile(customers):
    return customers[0]


# ── Normal transaction ────────────────────────────────────────────────────────


class TestNormalTransaction:
    def test_is_not_fraud(self, profile):
        txn = make_normal_transaction(profile)
        assert txn.is_fraud is False
        assert txn.fraud_scenario is None

    def test_internal_fields_not_in_payload(self, profile):
        payload = make_normal_transaction(profile).model_dump()
        assert "is_fraud" not in payload
        assert "fraud_scenario" not in payload

    def test_amount_is_positive(self, profile):
        for _ in range(20):
            txn = make_normal_transaction(profile)
            assert txn.amount > 0

    def test_uses_known_device(self, profile):
        for _ in range(30):
            txn = make_normal_transaction(profile)
            assert txn.device_id in profile.registered_devices

    def test_country_matches_home(self, profile):
        txn = make_normal_transaction(profile)
        assert txn.country_code == profile.home_country

    def test_account_belongs_to_customer(self, profile):
        txn = make_normal_transaction(profile)
        assert txn.account_id in profile.account_ids

    def test_occurred_at_is_iso8601(self, profile):
        txn = make_normal_transaction(profile)
        assert txn.occurred_at.endswith("Z")
        datetime.fromisoformat(txn.occurred_at.replace("Z", "+00:00"))


# ── Velocity fraud ────────────────────────────────────────────────────────────


class TestVelocityFraud:
    def test_produces_multiple_transactions(self, profile):
        txns = make_velocity_fraud(profile)
        assert len(txns) >= 6

    def test_all_marked_fraud(self, profile):
        for txn in make_velocity_fraud(profile):
            assert txn.is_fraud is True
            assert txn.fraud_scenario == "velocity"

    def test_all_card_not_present(self, profile):
        for txn in make_velocity_fraud(profile):
            assert txn.channel == "card_not_present"

    def test_small_amounts(self, profile):
        for txn in make_velocity_fraud(profile):
            assert 1.0 <= txn.amount <= 15.0

    def test_same_account(self, profile):
        txns = make_velocity_fraud(profile)
        account_ids = {t.account_id for t in txns}
        assert len(account_ids) == 1, "Velocity fraud should use one account"


# ── Geo impossible ────────────────────────────────────────────────────────────


class TestGeoImpossible:
    def test_is_fraud(self, profile):
        txn = make_geo_impossible_transaction(profile)
        assert txn.is_fraud is True
        assert txn.fraud_scenario == "geo_impossible"

    def test_different_country(self, profile):
        for _ in range(10):
            txn = make_geo_impossible_transaction(profile)
            assert txn.country_code != profile.home_country

    def test_coordinates_differ_significantly(self, profile):
        txn = make_geo_impossible_transaction(profile)
        dist = abs(txn.latitude - profile.home_lat) + abs(txn.longitude - profile.home_lon)
        assert dist > 5, "Remote transaction should be far from home"


# ── Account takeover ──────────────────────────────────────────────────────────


class TestAccountTakeover:
    def test_is_fraud(self, profile):
        txn = make_account_takeover_transaction(profile)
        assert txn.is_fraud is True
        assert txn.fraud_scenario == "account_takeover"

    def test_new_device(self, profile):
        for _ in range(20):
            txn = make_account_takeover_transaction(profile)
            assert txn.device_id not in profile.registered_devices

    def test_high_value_amount(self, profile):
        for _ in range(10):
            txn = make_account_takeover_transaction(profile)
            assert txn.amount >= 500

    def test_cnp_channel(self, profile):
        txn = make_account_takeover_transaction(profile)
        assert txn.channel == "card_not_present"


# ── CNP spike ─────────────────────────────────────────────────────────────────


class TestCnpSpike:
    def test_produces_many_transactions(self, profile):
        txns = make_cnp_spike_transactions(profile)
        assert len(txns) >= 10

    def test_all_cnp(self, profile):
        for txn in make_cnp_spike_transactions(profile):
            assert txn.channel == "card_not_present"

    def test_escalating_amounts(self, profile):
        txns = make_cnp_spike_transactions(profile)
        amounts = [t.amount for t in txns]
        assert amounts[-1] > amounts[0], "Amounts should escalate"

    def test_same_card(self, profile):
        txns = make_cnp_spike_transactions(profile)
        cards = {t.card_last4 for t in txns}
        assert len(cards) == 1, "CNP spike should be on one card"


# ── Unusual MCC ───────────────────────────────────────────────────────────────


class TestUnusualMcc:
    def test_is_fraud(self, profile):
        for _ in range(10):
            txn = make_unusual_mcc_transaction(profile)
            assert txn.is_fraud is True
            assert txn.fraud_scenario == "unusual_mcc"

    def test_high_risk_mcc(self, profile):
        for _ in range(20):
            txn = make_unusual_mcc_transaction(profile)
            assert txn.merchant_category_code in {"6011", "7995", "6051"}

    def test_odd_hours(self, profile):
        for _ in range(20):
            txn = make_unusual_mcc_transaction(profile)
            dt = datetime.fromisoformat(txn.occurred_at.replace("Z", "+00:00"))
            assert 2 <= dt.hour <= 4, f"Expected 2-4am, got hour={dt.hour}"


# ── Structuring ───────────────────────────────────────────────────────────────


class TestStructuring:
    def test_produces_multiple_transactions(self, profile):
        txns = make_structuring_transactions(profile, 10000.0)
        assert len(txns) >= 2

    def test_amounts_below_threshold(self, profile):
        for txn in make_structuring_transactions(profile, 10000.0):
            assert 9000 <= txn.amount <= 9999, f"Amount {txn.amount} outside band"

    def test_custom_threshold(self, profile):
        for txn in make_structuring_transactions(profile, 5000.0):
            assert 4000 <= txn.amount <= 4999

    def test_atm_channel(self, profile):
        for txn in make_structuring_transactions(profile, 10000.0):
            assert txn.channel == "atm"

    def test_same_account(self, profile):
        txns = make_structuring_transactions(profile, 10000.0)
        assert len({t.account_id for t in txns}) == 1


# ── generate_transaction_batch ────────────────────────────────────────────────


class TestGenerateBatch:
    def test_zero_fraud_rate_produces_no_fraud(self, customers):
        random.seed(1)
        for _ in range(200):
            for txn in generate_transaction_batch(customers, 0.0, 10000.0):
                assert txn.is_fraud is False

    def test_full_fraud_rate_produces_fraud(self, customers):
        random.seed(2)
        seen_fraud = False
        for _ in range(20):
            for txn in generate_transaction_batch(customers, 1.0, 10000.0):
                if txn.is_fraud:
                    seen_fraud = True
        assert seen_fraud

    def test_payload_never_leaks_internal_fields(self, customers):
        random.seed(3)
        for _ in range(100):
            for txn in generate_transaction_batch(customers, 0.5, 10000.0):
                payload = txn.model_dump()
                assert "is_fraud" not in payload
                assert "fraud_scenario" not in payload

    def test_all_scenarios_reachable(self, customers):
        random.seed(4)
        seen = set()
        for _ in range(500):
            for txn in generate_transaction_batch(customers, 1.0, 10000.0):
                if txn.fraud_scenario:
                    seen.add(txn.fraud_scenario)
        expected = {
            "velocity",
            "geo_impossible",
            "account_takeover",
            "cnp_spike",
            "unusual_mcc",
            "structuring",
        }
        assert seen == expected, f"Missing scenarios: {expected - seen}"
