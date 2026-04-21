from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from faker import Faker

fake = Faker("en_AU")
random.seed(42)

# City coordinates for home location assignment
_CITY_COORDS = {
    "AU": [
        (-33.8688, 151.2093),  # Sydney
        (-37.8136, 144.9631),  # Melbourne
        (-27.4698, 153.0251),  # Brisbane
        (-31.9505, 115.8605),  # Perth
        (-34.9285, 138.6007),  # Adelaide
        (-42.8821, 147.3272),  # Hobart
        (-35.2809, 149.1300),  # Canberra
        (-12.4634, 130.8456),  # Darwin
    ],
    "GB": [
        (51.5074, -0.1278),  # London
        (53.4808, -2.2426),  # Manchester
        (52.4862, -1.8904),  # Birmingham
    ],
    "US": [
        (40.7128, -74.0060),  # New York
        (34.0522, -118.2437),  # Los Angeles
        (41.8781, -87.6298),  # Chicago
    ],
    "SG": [(1.3521, 103.8198)],
    "NZ": [(-36.8485, 174.7633)],
    "HK": [(22.3193, 114.1694)],
}

_COUNTRY_WEIGHTS = {
    "AU": 0.85,
    "GB": 0.08,
    "US": 0.04,
    "SG": 0.01,
    "NZ": 0.01,
    "HK": 0.01,
}
_RISK_WEIGHTS = {"low": 0.80, "medium": 0.15, "high": 0.04, "pep": 0.01}

_MCC_MAP = {
    "5411": "Grocery Stores",
    "5912": "Drug Stores & Pharmacies",
    "5812": "Eating Places & Restaurants",
    "5541": "Service Stations",
    "7011": "Hotels & Motels",
    "5311": "Department Stores",
    "4111": "Transportation",
    "5732": "Electronics",
    "5621": "Women's Clothing",
}
_MCC_CODES = list(_MCC_MAP.keys())

_MERCHANT_NAMES = {
    "5411": ["Woolworths", "Coles", "IGA", "ALDI", "Harris Farm"],
    "5912": ["Chemist Warehouse", "Priceline", "Terry White", "Amcal"],
    "5812": ["McDonald's", "Grill'd", "Subway", "Nando's", "Guzman y Gomez"],
    "5541": ["BP", "Shell", "Caltex", "7-Eleven"],
    "7011": ["Marriott", "Hilton", "Accor", "Novotel", "ibis"],
    "5311": ["Myer", "David Jones", "Target", "Big W", "Kmart"],
    "4111": ["Opal Transit", "Translink", "Myki", "Uber"],
    "5732": ["JB Hi-Fi", "Harvey Norman", "Officeworks", "Apple"],
    "5621": ["Zara", "H&M", "Country Road", "Witchery"],
}


def _pick_country() -> str:
    countries = list(_COUNTRY_WEIGHTS.keys())
    weights = list(_COUNTRY_WEIGHTS.values())
    return random.choices(countries, weights=weights)[0]


def _pick_risk_tier() -> str:
    tiers = list(_RISK_WEIGHTS.keys())
    weights = list(_RISK_WEIGHTS.values())
    return random.choices(tiers, weights=weights)[0]


def _home_coords(country: str) -> tuple[float, float]:
    options = _CITY_COORDS.get(country, _CITY_COORDS["AU"])
    base_lat, base_lon = random.choice(options)
    # Add ±0.3 degree jitter for suburb-level variation
    return (
        round(base_lat + random.uniform(-0.3, 0.3), 6),
        round(base_lon + random.uniform(-0.3, 0.3), 6),
    )


def _make_merchant_pool(size: int = 8) -> list[dict]:
    merchants = []
    for _ in range(size):
        mcc = random.choice(_MCC_CODES)
        names = _MERCHANT_NAMES.get(mcc, ["Generic Store"])
        merchants.append(
            {
                "merchant_id": str(uuid.uuid4()),
                "merchant_name": f"{random.choice(names)} {fake.city()}",
                "merchant_category_code": mcc,
            }
        )
    return merchants


@dataclass
class CustomerProfile:
    customer_id: str
    name: str
    risk_tier: str
    home_country: str
    home_lat: float
    home_lon: float
    typical_txn_amount: float
    typical_txn_std: float
    registered_devices: list[str]
    preferred_merchants: list[dict]
    account_ids: list[str]
    card_last4s: list[str]


def build_customer_pool(size: int = 500) -> list[CustomerProfile]:
    """Generate a deterministic synthetic customer population.

    The pool is generated once at startup and reused by all event generators
    to keep customer/account relationships internally consistent.
    """
    customers = []
    for _ in range(size):
        country = _pick_country()
        lat, lon = _home_coords(country)
        num_accounts = random.choices([1, 2], weights=[0.7, 0.3])[0]
        customers.append(
            CustomerProfile(
                customer_id=str(uuid.uuid4()),
                name=fake.name(),
                risk_tier=_pick_risk_tier(),
                home_country=country,
                home_lat=lat,
                home_lon=lon,
                typical_txn_amount=round(random.uniform(15, 200), 2),
                typical_txn_std=round(random.uniform(5, 50), 2),
                registered_devices=[str(uuid.uuid4()) for _ in range(random.randint(1, 3))],
                preferred_merchants=_make_merchant_pool(random.randint(5, 10)),
                account_ids=[str(uuid.uuid4()) for _ in range(num_accounts)],
                card_last4s=[str(random.randint(1000, 9999)) for _ in range(num_accounts)],
            )
        )
    return customers
