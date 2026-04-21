"""Tests for login event generators."""

import random

import pytest

from generators.customer_pool import build_customer_pool
from generators.login import (
    generate_login_event,
    make_brute_force_login_storm,
    make_failed_login,
    make_normal_login,
)


@pytest.fixture(scope="module")
def customers():
    random.seed(10)
    return build_customer_pool(20)


@pytest.fixture(scope="module")
def profile(customers):
    return customers[0]


class TestNormalLogin:
    def test_success_is_true(self, profile):
        evt = make_normal_login(profile)
        assert evt.success is True
        assert evt.failure_reason is None

    def test_uses_known_device(self, profile):
        for _ in range(20):
            evt = make_normal_login(profile)
            assert evt.device_id in profile.registered_devices

    def test_home_country(self, profile):
        evt = make_normal_login(profile)
        assert evt.country_code == profile.home_country


class TestFailedLogin:
    def test_success_is_false(self, profile):
        evt = make_failed_login(profile)
        assert evt.success is False
        assert evt.failure_reason is not None

    def test_uses_unknown_device(self, profile):
        for _ in range(20):
            evt = make_failed_login(profile)
            assert evt.device_id not in profile.registered_devices


class TestBruteForceLoginStorm:
    def test_produces_multiple_failures(self, profile):
        events = make_brute_force_login_storm(profile)
        assert 3 <= len(events) <= 5

    def test_all_failures(self, profile):
        for evt in make_brute_force_login_storm(profile):
            assert evt.success is False

    def test_same_device_and_ip(self, profile):
        events = make_brute_force_login_storm(profile)
        devices = {e.device_id for e in events}
        ips = {e.ip_address for e in events}
        assert len(devices) == 1, "Brute force should use same device"
        assert len(ips) == 1, "Brute force should use same IP"

    def test_same_customer(self, profile):
        for evt in make_brute_force_login_storm(profile):
            assert evt.customer_id == profile.customer_id


class TestGenerateLoginEvent:
    def test_zero_fraud_produces_successes(self, customers):
        random.seed(5)
        events = [generate_login_event(customers, 0.0)[0] for _ in range(50)]
        assert all(e.success for e in events)

    def test_high_fraud_produces_failures(self, customers):
        random.seed(6)
        events = []
        for _ in range(100):
            events.extend(generate_login_event(customers, 1.0))
        failures = [e for e in events if not e.success]
        assert len(failures) > 0
