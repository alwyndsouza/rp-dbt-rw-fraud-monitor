"""Tests for the synthetic customer pool generator."""

import random

import pytest

from generators.customer_pool import CustomerProfile, build_customer_pool


@pytest.fixture(scope="module")
def pool():
    random.seed(42)
    return build_customer_pool(50)


def test_pool_size(pool):
    assert len(pool) == 50


def test_customer_profile_structure(pool):
    for customer in pool:
        assert isinstance(customer, CustomerProfile)
        assert customer.customer_id
        assert customer.home_country in {"AU", "GB", "US", "SG", "NZ", "HK"}
        assert customer.risk_tier in {"low", "medium", "high", "pep", "sanctioned"}
        assert 1 <= len(customer.registered_devices) <= 3
        assert 5 <= len(customer.preferred_merchants) <= 10
        assert 1 <= len(customer.account_ids) <= 2
        assert len(customer.card_last4s) == len(customer.account_ids)
        assert customer.typical_txn_amount > 0
        assert customer.typical_txn_std > 0


def test_risk_tier_distribution(pool):
    tiers = [c.risk_tier for c in pool]
    low_count = tiers.count("low")
    # With 50 customers and 80% weight, expect 30-50 low-risk
    assert low_count >= 20, f"Expected majority low-risk, got {low_count}/50"


def test_au_majority(pool):
    au_count = sum(1 for c in pool if c.home_country == "AU")
    # 85% weight → expect 30+ out of 50
    assert au_count >= 25, f"Expected AU majority, got {au_count}/50"


def test_home_coords_are_realistic(pool):
    for c in pool:
        assert -90 <= c.home_lat <= 90
        assert -180 <= c.home_lon <= 180


def test_merchant_pool_structure(pool):
    for c in pool:
        for m in c.preferred_merchants:
            assert "merchant_id" in m
            assert "merchant_name" in m
            assert "merchant_category_code" in m


def test_unique_customer_ids(pool):
    ids = [c.customer_id for c in pool]
    assert len(ids) == len(set(ids)), "Duplicate customer_ids found"
