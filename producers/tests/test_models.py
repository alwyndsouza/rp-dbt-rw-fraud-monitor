"""Tests for Pydantic event models — verify serialisation and field exclusion."""

from models import AlertEvent, LoginEvent, TransactionEvent


def _base_txn(**overrides):
    defaults = {
        "transaction_id": "txn-1",
        "account_id": "acc-1",
        "customer_id": "cust-1",
        "amount": 99.99,
        "merchant_id": "merch-1",
        "merchant_category_code": "5411",
        "merchant_name": "Woolworths",
        "channel": "card_present",
        "card_last4": "1234",
        "device_id": "dev-1",
        "ip_address": "1.2.3.4",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "country_code": "AU",
        "occurred_at": "2026-04-18T10:00:00.000Z",
    }
    defaults.update(overrides)
    return TransactionEvent(**defaults)


class TestTransactionEvent:
    def test_internal_fields_excluded_from_serialisation(self):
        txn = _base_txn(is_fraud=True, fraud_scenario="velocity")
        payload = txn.model_dump()
        assert "is_fraud" not in payload
        assert "fraud_scenario" not in payload

    def test_internal_fields_readable_on_instance(self):
        txn = _base_txn(is_fraud=True, fraud_scenario="geo_impossible")
        assert txn.is_fraud is True
        assert txn.fraud_scenario == "geo_impossible"

    def test_defaults(self):
        txn = _base_txn()
        assert txn.currency == "AUD"
        assert txn.status == "pending"
        assert txn.is_fraud is False
        assert txn.fraud_scenario is None

    def test_json_round_trip(self):
        txn = _base_txn(amount=249.95)
        data = txn.model_dump()
        txn2 = TransactionEvent(**data)
        assert txn2.amount == 249.95

    def test_payload_has_expected_keys(self):
        expected = {
            "transaction_id",
            "account_id",
            "customer_id",
            "amount",
            "currency",
            "merchant_id",
            "merchant_category_code",
            "merchant_name",
            "channel",
            "card_last4",
            "device_id",
            "ip_address",
            "latitude",
            "longitude",
            "country_code",
            "occurred_at",
            "status",
        }
        assert set(_base_txn().model_dump().keys()) == expected


class TestLoginEvent:
    def test_successful_login(self):
        evt = LoginEvent(
            event_id="evt-1",
            customer_id="cust-1",
            device_id="dev-1",
            ip_address="1.2.3.4",
            country_code="AU",
            latitude=-33.0,
            longitude=151.0,
            user_agent="UA",
            success=True,
            failure_reason=None,
            occurred_at="2026-04-18T10:00:00.000Z",
        )
        assert evt.success is True
        assert evt.failure_reason is None

    def test_failed_login(self):
        evt = LoginEvent(
            event_id="evt-2",
            customer_id="cust-1",
            device_id="dev-x",
            ip_address="9.9.9.9",
            country_code="CN",
            latitude=39.9,
            longitude=116.4,
            user_agent="UA",
            success=False,
            failure_reason="wrong_password",
            occurred_at="2026-04-18T10:00:01.000Z",
        )
        assert evt.success is False
        assert evt.failure_reason == "wrong_password"


class TestAlertEvent:
    def test_confidence_score_range(self):
        alert = AlertEvent(
            alert_id="alt-1",
            customer_id="cust-1",
            transaction_id="txn-1",
            alert_type="velocity",
            severity="high",
            confidence_score=0.87,
            rule_id="RULE_001",
            occurred_at="2026-04-18T10:00:02.000Z",
        )
        assert 0.0 <= alert.confidence_score <= 1.0
