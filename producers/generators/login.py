from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from generators.customer_pool import CustomerProfile
from models import LoginEvent

fake = Faker()

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1 WebKit/17619",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1 Safari/605.1",
    "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36",
]

_FAILURE_REASONS = ["wrong_password", "account_locked", "2fa_failed", "session_expired"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def make_normal_login(profile: CustomerProfile) -> LoginEvent:
    return LoginEvent(
        event_id=str(uuid.uuid4()),
        customer_id=profile.customer_id,
        device_id=random.choice(profile.registered_devices),
        ip_address=fake.ipv4(),
        country_code=profile.home_country,
        latitude=round(profile.home_lat + random.uniform(-0.05, 0.05), 6),
        longitude=round(profile.home_lon + random.uniform(-0.05, 0.05), 6),
        user_agent=random.choice(_USER_AGENTS),
        success=True,
        failure_reason=None,
        occurred_at=_now_iso(),
    )


def make_failed_login(profile: CustomerProfile) -> LoginEvent:
    """Single failed login — new device, possibly foreign IP."""
    use_foreign = random.random() < 0.4
    if use_foreign:
        country_code = random.choice(["CN", "RU", "NG", "BR", "RO"])
        lat = round(random.uniform(-60, 60), 6)
        lon = round(random.uniform(-180, 180), 6)
    else:
        country_code = profile.home_country
        lat = round(profile.home_lat + random.uniform(-1, 1), 6)
        lon = round(profile.home_lon + random.uniform(-1, 1), 6)

    return LoginEvent(
        event_id=str(uuid.uuid4()),
        customer_id=profile.customer_id,
        device_id=str(uuid.uuid4()),  # unknown device
        ip_address=fake.ipv4(),
        country_code=country_code,
        latitude=lat,
        longitude=lon,
        user_agent=random.choice(_USER_AGENTS),
        success=False,
        failure_reason=random.choice(_FAILURE_REASONS),
        occurred_at=_now_iso(),
    )


def make_brute_force_login_storm(profile: CustomerProfile) -> list[LoginEvent]:
    """3-5 rapid failed logins preceding an account takeover attempt."""
    base_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    events = []
    attacker_ip = fake.ipv4()
    attacker_device = str(uuid.uuid4())
    country_code = random.choice(["CN", "RU", "NG", "BR"])

    for _i in range(random.randint(3, 5)):
        t = base_time + timedelta(seconds=random.randint(0, 55))
        events.append(
            LoginEvent(
                event_id=str(uuid.uuid4()),
                customer_id=profile.customer_id,
                device_id=attacker_device,
                ip_address=attacker_ip,
                country_code=country_code,
                latitude=round(random.uniform(-60, 60), 6),
                longitude=round(random.uniform(-180, 180), 6),
                user_agent=random.choice(_USER_AGENTS),
                success=False,
                failure_reason="wrong_password",
                occurred_at=t.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            )
        )
    return events


def generate_login_event(
    customers: list[CustomerProfile],
    fraud_rate: float,
) -> list[LoginEvent]:
    profile = random.choice(customers)
    roll = random.random()

    if roll < fraud_rate * 0.5:
        return make_brute_force_login_storm(profile)
    elif roll < fraud_rate:
        return [make_failed_login(profile)]
    else:
        return [make_normal_login(profile)]
