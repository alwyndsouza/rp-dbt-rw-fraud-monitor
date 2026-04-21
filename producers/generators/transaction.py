from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from generators.customer_pool import CustomerProfile
from models import TransactionEvent

fake = Faker()

# High-risk MCCs for unusual-hours fraud scenario
_HIGH_RISK_MCC = ["6011", "7995", "6051"]
_REMOTE_COUNTRIES = {
    "AU": [
        ("GB", 51.5074, -0.1278),
        ("US", 40.7128, -74.0060),
        ("SG", 1.3521, 103.8198),
    ],
    "GB": [
        ("AU", -33.8688, 151.2093),
        ("US", 40.7128, -74.0060),
        ("CN", 39.9042, 116.4074),
    ],
    "US": [
        ("AU", -33.8688, 151.2093),
        ("GB", 51.5074, -0.1278),
        ("JP", 35.6762, 139.6503),
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _near_coords(lat: float, lon: float, radius_km: float = 50) -> tuple[float, float]:
    delta = radius_km / 111.0
    return (
        round(lat + random.uniform(-delta, delta), 6),
        round(lon + random.uniform(-delta, delta), 6),
    )


def _normal_amount(profile: CustomerProfile) -> float:
    amount = random.gauss(profile.typical_txn_amount, profile.typical_txn_std)
    return round(max(1.0, amount), 2)


def make_normal_transaction(profile: CustomerProfile) -> TransactionEvent:
    merchant = random.choice(profile.preferred_merchants)
    account_idx = random.randrange(len(profile.account_ids))
    lat, lon = _near_coords(profile.home_lat, profile.home_lon)

    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        account_id=profile.account_ids[account_idx],
        customer_id=profile.customer_id,
        amount=_normal_amount(profile),
        currency="AUD",
        merchant_id=merchant["merchant_id"],
        merchant_category_code=merchant["merchant_category_code"],
        merchant_name=merchant["merchant_name"],
        channel=random.choices(
            ["card_present", "card_not_present", "transfer"],
            weights=[0.65, 0.30, 0.05],
        )[0],
        card_last4=profile.card_last4s[account_idx],
        device_id=random.choice(profile.registered_devices),
        ip_address=fake.ipv4(),
        latitude=lat,
        longitude=lon,
        country_code=profile.home_country,
        occurred_at=_now_iso(),
        status="approved",
        is_fraud=False,
    )


# ---------------------------------------------------------------------------
# Fraud scenario generators
# ---------------------------------------------------------------------------


def make_velocity_fraud(profile: CustomerProfile) -> list[TransactionEvent]:
    """6+ small card-not-present transactions within 60 seconds."""
    account_idx = random.randrange(len(profile.account_ids))
    base_time = datetime.now(timezone.utc)
    merchant = random.choice(profile.preferred_merchants)
    txns = []
    for _i in range(random.randint(6, 9)):
        t = base_time + timedelta(seconds=random.randint(0, 55))
        txns.append(
            TransactionEvent(
                transaction_id=str(uuid.uuid4()),
                account_id=profile.account_ids[account_idx],
                customer_id=profile.customer_id,
                amount=round(random.uniform(1.0, 15.0), 2),
                currency="AUD",
                merchant_id=merchant["merchant_id"],
                merchant_category_code=merchant["merchant_category_code"],
                merchant_name=merchant["merchant_name"],
                channel="card_not_present",
                card_last4=profile.card_last4s[account_idx],
                device_id=random.choice(profile.registered_devices),
                ip_address=fake.ipv4(),
                latitude=profile.home_lat,
                longitude=profile.home_lon,
                country_code=profile.home_country,
                occurred_at=t.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                status="pending",
                is_fraud=True,
                fraud_scenario="velocity",
            )
        )
    return txns


def make_geo_impossible_transaction(profile: CustomerProfile) -> TransactionEvent:
    """Transaction 5000+ km from home — impossible travel time."""
    remote_options = _REMOTE_COUNTRIES.get(profile.home_country, [("GB", 51.5074, -0.1278)])
    country_code, lat, lon = random.choice(remote_options)
    account_idx = random.randrange(len(profile.account_ids))
    merchant = random.choice(profile.preferred_merchants)

    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        account_id=profile.account_ids[account_idx],
        customer_id=profile.customer_id,
        amount=round(random.uniform(50, 800), 2),
        currency="AUD",
        merchant_id=merchant["merchant_id"],
        merchant_category_code=merchant["merchant_category_code"],
        merchant_name=f"{merchant['merchant_name']} (Overseas)",
        channel="card_present",
        card_last4=profile.card_last4s[account_idx],
        device_id=random.choice(profile.registered_devices),
        ip_address=fake.ipv4(),
        latitude=round(lat + random.uniform(-0.5, 0.5), 6),
        longitude=round(lon + random.uniform(-0.5, 0.5), 6),
        country_code=country_code,
        occurred_at=_now_iso(),
        status="pending",
        is_fraud=True,
        fraud_scenario="geo_impossible",
    )


def make_account_takeover_transaction(profile: CustomerProfile) -> TransactionEvent:
    """New device + new IP + high-value transaction."""
    account_idx = random.randrange(len(profile.account_ids))
    merchant = random.choice(profile.preferred_merchants)
    new_device_id = str(uuid.uuid4())  # not in registered_devices

    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        account_id=profile.account_ids[account_idx],
        customer_id=profile.customer_id,
        amount=round(random.uniform(500, 5000), 2),
        currency="AUD",
        merchant_id=merchant["merchant_id"],
        merchant_category_code=merchant["merchant_category_code"],
        merchant_name=merchant["merchant_name"],
        channel="card_not_present",
        card_last4=profile.card_last4s[account_idx],
        device_id=new_device_id,
        ip_address=fake.ipv4(),
        latitude=round(profile.home_lat + random.uniform(-2, 2), 6),
        longitude=round(profile.home_lon + random.uniform(-2, 2), 6),
        country_code=profile.home_country,
        occurred_at=_now_iso(),
        status="pending",
        is_fraud=True,
        fraud_scenario="account_takeover",
    )


def make_cnp_spike_transactions(profile: CustomerProfile) -> list[TransactionEvent]:
    """10+ card-not-present transactions in 5 minutes with escalating amounts."""
    account_idx = random.randrange(len(profile.account_ids))
    base_time = datetime.now(timezone.utc)
    merchant = random.choice(profile.preferred_merchants)
    txns = []
    base_amount = random.uniform(20, 100)
    for i in range(random.randint(10, 14)):
        t = base_time + timedelta(seconds=random.randint(0, 290))
        txns.append(
            TransactionEvent(
                transaction_id=str(uuid.uuid4()),
                account_id=profile.account_ids[account_idx],
                customer_id=profile.customer_id,
                amount=round(base_amount * (1 + i * 0.15), 2),
                currency="AUD",
                merchant_id=merchant["merchant_id"],
                merchant_category_code=merchant["merchant_category_code"],
                merchant_name=merchant["merchant_name"],
                channel="card_not_present",
                card_last4=profile.card_last4s[account_idx],
                device_id=random.choice(profile.registered_devices),
                ip_address=fake.ipv4(),
                latitude=profile.home_lat,
                longitude=profile.home_lon,
                country_code=profile.home_country,
                occurred_at=t.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                status="pending",
                is_fraud=True,
                fraud_scenario="cnp_spike",
            )
        )
    return txns


def make_unusual_mcc_transaction(profile: CustomerProfile) -> TransactionEvent:
    """ATM or gambling transaction at 2-4am."""
    mcc = random.choice(_HIGH_RISK_MCC)
    mcc_names = {
        "6011": "ATM Cash Withdrawal",
        "7995": "Online Gambling",
        "6051": "Crypto Exchange",
    }
    account_idx = random.randrange(len(profile.account_ids))

    # Set time to early morning
    now = datetime.now(timezone.utc)
    odd_hour = now.replace(hour=random.randint(2, 4), minute=random.randint(0, 59))
    lat, lon = _near_coords(profile.home_lat, profile.home_lon, 20)

    return TransactionEvent(
        transaction_id=str(uuid.uuid4()),
        account_id=profile.account_ids[account_idx],
        customer_id=profile.customer_id,
        amount=round(random.uniform(200, 2000), 2),
        currency="AUD",
        merchant_id=str(uuid.uuid4()),
        merchant_category_code=mcc,
        merchant_name=mcc_names.get(mcc, "Unknown"),
        channel=random.choice(["atm", "card_not_present"]),
        card_last4=profile.card_last4s[account_idx],
        device_id=random.choice(profile.registered_devices),
        ip_address=fake.ipv4(),
        latitude=lat,
        longitude=lon,
        country_code=profile.home_country,
        occurred_at=odd_hour.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        status="pending",
        is_fraud=True,
        fraud_scenario="unusual_mcc",
    )


def make_structuring_transactions(
    profile: CustomerProfile, threshold: float = 10000.0
) -> list[TransactionEvent]:
    """Multiple transactions just below AUSTRAC reporting threshold."""
    account_idx = random.randrange(len(profile.account_ids))
    base_time = datetime.now(timezone.utc)
    merchant = random.choice(profile.preferred_merchants)
    txns = []
    for _i in range(random.randint(2, 4)):
        amount = round(threshold - random.uniform(100, 400), 2)
        t = base_time + timedelta(minutes=random.randint(0, 50))
        txns.append(
            TransactionEvent(
                transaction_id=str(uuid.uuid4()),
                account_id=profile.account_ids[account_idx],
                customer_id=profile.customer_id,
                amount=amount,
                currency="AUD",
                merchant_id=merchant["merchant_id"],
                merchant_category_code="6011",
                merchant_name="ATM Cash Withdrawal",
                channel="atm",
                card_last4=profile.card_last4s[account_idx],
                device_id=random.choice(profile.registered_devices),
                ip_address=fake.ipv4(),
                latitude=round(profile.home_lat + random.uniform(-0.1, 0.1), 6),
                longitude=round(profile.home_lon + random.uniform(-0.1, 0.1), 6),
                country_code=profile.home_country,
                occurred_at=t.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                status="pending",
                is_fraud=True,
                fraud_scenario="structuring",
            )
        )
    return txns


_FRAUD_SCENARIOS = [
    "velocity",
    "geo_impossible",
    "account_takeover",
    "cnp_spike",
    "unusual_mcc",
    "structuring",
]


def generate_transaction_batch(
    customers: list[CustomerProfile],
    fraud_rate: float,
    structuring_threshold: float,
) -> list[TransactionEvent]:
    """Generate a single transaction or fraud burst."""
    profile = random.choice(customers)

    if random.random() < fraud_rate:
        scenario = random.choice(_FRAUD_SCENARIOS)
        if scenario == "velocity":
            return make_velocity_fraud(profile)
        elif scenario == "geo_impossible":
            return [make_geo_impossible_transaction(profile)]
        elif scenario == "account_takeover":
            return [make_account_takeover_transaction(profile)]
        elif scenario == "cnp_spike":
            return make_cnp_spike_transactions(profile)
        elif scenario == "unusual_mcc":
            return [make_unusual_mcc_transaction(profile)]
        elif scenario == "structuring":
            return make_structuring_transactions(profile, structuring_threshold)

    return [make_normal_transaction(profile)]
