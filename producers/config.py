"""Runtime configuration for the synthetic fraud event producer.

All values are read from environment variables so the producer can run
unchanged in local Docker Compose and production orchestrators.
"""

import os

REDPANDA_BROKERS = os.environ.get("REDPANDA_BROKERS", "localhost:9092").split(",")
REDPANDA_SECURITY_PROTOCOL = os.environ.get("REDPANDA_SECURITY_PROTOCOL", "PLAINTEXT")
REDPANDA_SASL_MECHANISM = os.environ.get("REDPANDA_SASL_MECHANISM", "")
REDPANDA_SASL_USERNAME = os.environ.get("REDPANDA_SASL_USERNAME", "")
REDPANDA_SASL_PASSWORD = os.environ.get("REDPANDA_SASL_PASSWORD", "")

FRAUD_RATE = float(os.environ.get("FRAUD_RATE", "0.10"))
TRANSACTION_RATE = float(os.environ.get("TRANSACTION_RATE", "20"))
LOGIN_RATE = float(os.environ.get("LOGIN_RATE", "5"))
CARD_RATE = float(os.environ.get("CARD_RATE", "1"))
ALERT_RATE = float(os.environ.get("ALERT_RATE", "8"))
KYC_RATE = float(os.environ.get("KYC_RATE", "0.5"))
CUSTOMER_POOL_SIZE = int(os.environ.get("CUSTOMER_POOL_SIZE", "500"))
STRUCTURING_THRESHOLD = float(os.environ.get("STRUCTURING_THRESHOLD", "10000"))

# Minute-tick heartbeat: guarantees a batch of events every 60s on minute
# boundaries regardless of per-second producer health. Seeds every 1-minute
# RisingWave tumbling window with at least some input.
MINUTE_TICK_ENABLED = os.environ.get("MINUTE_TICK_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)
MINUTE_TICK_TRANSACTIONS = int(os.environ.get("MINUTE_TICK_TRANSACTIONS", "30"))
MINUTE_TICK_LOGINS = int(os.environ.get("MINUTE_TICK_LOGINS", "10"))

# Liveness probe: HTTP server port for container healthchecks. 0 disables.
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8000"))
ALERT_WORKERS = int(os.environ.get("ALERT_WORKERS", "4"))
ALERT_QUEUE_SIZE = int(os.environ.get("ALERT_QUEUE_SIZE", "2000"))

TOPICS = {
    "transactions": "transactions",
    "login_events": "login_events",
    "card_events": "card_events",
    "alert_events": "alert_events",
    "kyc_profile_events": "kyc_profile_events",
    "dlq": "fraud_dlq",
}
