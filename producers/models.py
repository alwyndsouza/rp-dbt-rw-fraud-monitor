from __future__ import annotations

from pydantic import BaseModel, Field


class TransactionEvent(BaseModel):
    """Canonical transaction payload emitted to the `transactions` topic."""

    transaction_id: str
    account_id: str
    customer_id: str
    amount: float
    currency: str = "AUD"
    merchant_id: str
    merchant_category_code: str
    merchant_name: str
    channel: str  # card_present|card_not_present|atm|transfer
    card_last4: str
    device_id: str
    ip_address: str
    latitude: float
    longitude: float
    country_code: str
    occurred_at: str
    status: str = "pending"
    # internal metadata — stripped before publish
    is_fraud: bool = Field(default=False, exclude=True)
    fraud_scenario: str | None = Field(default=None, exclude=True)


class LoginEvent(BaseModel):
    """Authentication activity payload emitted to the `login_events` topic."""

    event_id: str
    customer_id: str
    device_id: str
    ip_address: str
    country_code: str
    latitude: float
    longitude: float
    user_agent: str
    success: bool
    failure_reason: str | None = None
    occurred_at: str


class CardEvent(BaseModel):
    """Card lifecycle or control action payload emitted to `card_events`."""

    event_id: str
    account_id: str
    customer_id: str
    card_last4: str
    event_type: str  # block|unblock|reissue|pin_change|limit_change
    initiated_by: str  # customer|bank|fraud_system
    occurred_at: str


class AlertEvent(BaseModel):
    """Fraud alert payload emitted to `alert_events`."""

    alert_id: str
    customer_id: str
    transaction_id: str
    alert_type: (
        str  # velocity|geo_anomaly|device_fingerprint|card_not_present|account_takeover|structuring
    )
    severity: str  # low|medium|high|critical
    confidence_score: float
    rule_id: str
    occurred_at: str


class KycProfileEvent(BaseModel):
    """Customer KYC/risk profile payload emitted to `kyc_profile_events`."""

    customer_id: str
    risk_tier: str  # low|medium|high|pep|sanctioned
    kyc_status: str  # verified|pending|failed|expired
    account_type: str  # personal|business|joint
    country_of_residence: str
    updated_at: str
