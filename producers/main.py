"""
Fraud Detection Streaming Pipeline — Event Producer

Publishes synthetic banking events to Redpanda at configurable rates.
Fraud injection rate is controlled by the FRAUD_RATE environment variable.
"""

from __future__ import annotations

import contextlib
import json
import logging
import queue
import signal
import sys
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

import config
from generators.alert import make_alert_for_transaction, make_noise_alert
from generators.card import generate_card_event
from generators.customer_pool import build_customer_pool
from generators.kyc_profile import generate_kyc_event
from generators.login import generate_login_event
from generators.transaction import generate_transaction_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("producer")

_stop_event = threading.Event()
_metrics_lock = threading.Lock()
_metrics: dict[str, int] = defaultdict(int)
_last_publish_at: float = 0.0
_alert_queue: queue.Queue = queue.Queue(maxsize=max(config.ALERT_QUEUE_SIZE, 100))
_ALERT_SENTINEL = object()


def _record_publish(topic: str) -> None:
    global _last_publish_at
    with _metrics_lock:
        _metrics[topic] += 1
        _last_publish_at = time.time()


def _signal_handler(sig, frame):
    log.info("Shutdown signal received — stopping producer.")
    _stop_event.set()


def _make_producer(retries: int = 10) -> KafkaProducer:
    for attempt in range(retries):
        try:
            producer_kwargs = {
                "bootstrap_servers": config.REDPANDA_BROKERS,
                "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
                "acks": "all",
                "retries": 3,
                "linger_ms": 5,
                "batch_size": 32768,
                "security_protocol": config.REDPANDA_SECURITY_PROTOCOL,
            }
            if config.REDPANDA_SECURITY_PROTOCOL.startswith("SASL"):
                producer_kwargs.update(
                    {
                        "sasl_mechanism": config.REDPANDA_SASL_MECHANISM or "SCRAM-SHA-256",
                        "sasl_plain_username": config.REDPANDA_SASL_USERNAME,
                        "sasl_plain_password": config.REDPANDA_SASL_PASSWORD,
                    }
                )
            producer = KafkaProducer(
                **producer_kwargs,
            )
            log.info("Connected to Redpanda at %s", config.REDPANDA_BROKERS)
            return producer
        except NoBrokersAvailable:
            wait = 2**attempt
            log.warning(
                "Brokers not available (attempt %d/%d). Retrying in %ds…",
                attempt + 1,
                retries,
                wait,
            )
            time.sleep(wait)
    log.error("Could not connect to Redpanda after %d attempts. Exiting.", retries)
    sys.exit(1)


def _publish(producer: KafkaProducer, topic: str, payload: dict, dlq_on_error: bool = True) -> None:
    try:
        producer.send(topic, value=payload)
        _record_publish(topic)
    except Exception as exc:
        log.error("Failed to publish to %s: %s", topic, exc)
        if dlq_on_error:
            with contextlib.suppress(Exception):
                producer.send(
                    config.TOPICS["dlq"],
                    value={"topic": topic, "payload": payload, "error": str(exc)},
                )


def run_transaction_producer(producer: KafkaProducer) -> None:
    interval = 1.0 / max(config.TRANSACTION_RATE, 0.1)
    log.info(
        "Transaction producer: %.1f/s (fraud_rate=%.0f%%)",
        config.TRANSACTION_RATE,
        config.FRAUD_RATE * 100,
    )

    while not _stop_event.is_set():
        t0 = time.monotonic()
        try:
            txns = generate_transaction_batch(
                customers, config.FRAUD_RATE, config.STRUCTURING_THRESHOLD
            )
            for txn in txns:
                payload = txn.model_dump()
                _publish(producer, config.TOPICS["transactions"], payload)

                if txn.is_fraud and txn.fraud_scenario:
                    _enqueue_reactive_alert(txn)
        except Exception as exc:
            log.exception("Transaction generator error: %s", exc)

        elapsed = time.monotonic() - t0
        sleep_time = max(0, interval - elapsed)
        _stop_event.wait(sleep_time)


def _emit_reactive_alert(producer: KafkaProducer, txn) -> None:
    """Emit alert after artificial rule-engine latency (100-800ms)."""
    try:
        alert = make_alert_for_transaction(txn)
        if alert:
            _publish(producer, config.TOPICS["alert_events"], alert.model_dump())
    except Exception as exc:
        log.debug("Alert emit error: %s", exc)


def _enqueue_reactive_alert(txn) -> None:
    """Push fraud transactions into a bounded queue for async alert workers."""
    try:
        _alert_queue.put_nowait(txn)
    except queue.Full:
        log.warning("Reactive alert queue full; dropping alert for txn=%s", txn.transaction_id)
        with _metrics_lock:
            _metrics["reactive_alert_dropped"] += 1


def _alert_worker(producer: KafkaProducer) -> None:
    """Continuously process reactive alert tasks from the shared queue."""
    while not _stop_event.is_set():
        try:
            item = _alert_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is _ALERT_SENTINEL:
            _alert_queue.task_done()
            break
        _emit_reactive_alert(producer, item)
        _alert_queue.task_done()


def run_login_producer(producer: KafkaProducer) -> None:
    interval = 1.0 / max(config.LOGIN_RATE, 0.1)
    log.info("Login producer: %.1f/s", config.LOGIN_RATE)

    while not _stop_event.is_set():
        try:
            events = generate_login_event(customers, config.FRAUD_RATE)
            for evt in events:
                _publish(producer, config.TOPICS["login_events"], evt.model_dump())
        except Exception as exc:
            log.exception("Login generator error: %s", exc)
        _stop_event.wait(interval)


def run_card_producer(producer: KafkaProducer) -> None:
    interval = 1.0 / max(config.CARD_RATE, 0.1)
    log.info("Card event producer: %.1f/s", config.CARD_RATE)

    while not _stop_event.is_set():
        try:
            evt = generate_card_event(customers, config.FRAUD_RATE)
            _publish(producer, config.TOPICS["card_events"], evt.model_dump())
        except Exception as exc:
            log.exception("Card generator error: %s", exc)
        _stop_event.wait(interval)


def run_noise_alert_producer(producer: KafkaProducer) -> None:
    """Emit low-confidence noise alerts to test false-positive filtering."""
    interval = 1.0 / max(config.ALERT_RATE, 0.1)
    log.info("Noise alert producer: %.1f/s", config.ALERT_RATE)

    while not _stop_event.is_set():
        try:
            alert = make_noise_alert(customers)
            _publish(producer, config.TOPICS["alert_events"], alert.model_dump())
        except Exception as exc:
            log.exception("Alert generator error: %s", exc)
        _stop_event.wait(interval)


def run_kyc_producer(producer: KafkaProducer) -> None:
    interval = 1.0 / max(config.KYC_RATE, 0.01)
    log.info("KYC producer: %.2f/s", config.KYC_RATE)

    while not _stop_event.is_set():
        try:
            evt = generate_kyc_event(customers)
            _publish(producer, config.TOPICS["kyc_profile_events"], evt.model_dump())
        except Exception as exc:
            log.exception("KYC generator error: %s", exc)
        _stop_event.wait(interval)


def _seconds_until_next_minute() -> float:
    """Seconds remaining until the next wall-clock minute boundary."""
    now = time.time()
    return 60.0 - (now % 60.0)


def run_minute_tick_producer(producer: KafkaProducer) -> None:
    """Emit a guaranteed batch every 60s on wall-clock minute boundaries.

    This ensures the 1-minute tumbling RisingWave windows always have input,
    even if per-second producers are throttled, restarted, or slowed down.
    """
    log.info(
        "Minute-tick producer: %d txn + %d logins per minute",
        config.MINUTE_TICK_TRANSACTIONS,
        config.MINUTE_TICK_LOGINS,
    )

    # Align to the next minute boundary, then tick every 60s.
    _stop_event.wait(_seconds_until_next_minute())

    while not _stop_event.is_set():
        tick_start = time.monotonic()
        minute_start = time.strftime("%Y-%m-%dT%H:%M:00Z", time.gmtime())
        published = 0

        try:
            # Guaranteed transactions (with fraud injection)
            for _ in range(config.MINUTE_TICK_TRANSACTIONS):
                txns = generate_transaction_batch(
                    customers, config.FRAUD_RATE, config.STRUCTURING_THRESHOLD
                )
                for txn in txns:
                    _publish(producer, config.TOPICS["transactions"], txn.model_dump())
                    published += 1
                    if txn.is_fraud and txn.fraud_scenario:
                        _enqueue_reactive_alert(txn)

            # Guaranteed logins
            for _ in range(config.MINUTE_TICK_LOGINS):
                events = generate_login_event(customers, config.FRAUD_RATE)
                for evt in events:
                    _publish(producer, config.TOPICS["login_events"], evt.model_dump())
                    published += 1

            producer.flush(timeout=5)
        except Exception as exc:
            log.exception("Minute-tick error: %s", exc)

        with _metrics_lock:
            totals = dict(_metrics)
        log.info(
            "Minute tick %s: tick_emitted=%d | cumulative %s",
            minute_start,
            published,
            {k: v for k, v in totals.items() if v},
        )

        # Sleep until the next minute boundary (account for tick duration).
        elapsed = time.monotonic() - tick_start
        _stop_event.wait(max(1.0, 60.0 - elapsed))


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in ("/health", "/healthz", "/"):
            stale_seconds = time.time() - _last_publish_at if _last_publish_at else None
            healthy = _last_publish_at > 0 and (stale_seconds is None or stale_seconds < 120)
            with _metrics_lock:
                body = json.dumps(
                    {
                        "status": "ok" if healthy else "degraded",
                        "stale_seconds": stale_seconds,
                        "published_total": sum(_metrics.values()),
                        "published_by_topic": dict(_metrics),
                    }
                ).encode()
            self.send_response(200 if healthy else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_args, **_kwargs) -> None:  # silence default access log
        return


def _start_health_server() -> HTTPServer | None:
    if config.HEALTH_PORT <= 0:
        return None
    try:
        server = HTTPServer(("0.0.0.0", config.HEALTH_PORT), _HealthHandler)
    except OSError as exc:
        log.warning("Could not bind health server on :%d (%s) — skipping", config.HEALTH_PORT, exc)
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
    log.info("Liveness probe listening on :%d/health", config.HEALTH_PORT)
    return server


def main() -> None:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    health_server = _start_health_server()

    log.info("Building customer pool (%d customers)…", config.CUSTOMER_POOL_SIZE)
    global customers
    customers = build_customer_pool(config.CUSTOMER_POOL_SIZE)
    log.info("Customer pool ready.")

    producer = _make_producer()

    # Emit initial KYC profiles for entire customer pool
    log.info("Seeding KYC profiles…")
    for cust in customers:
        evt = generate_kyc_event([cust])
        _publish(producer, config.TOPICS["kyc_profile_events"], evt.model_dump())
    producer.flush()
    log.info("KYC seed complete.")

    threads = [
        threading.Thread(
            target=run_transaction_producer,
            args=(producer,),
            daemon=True,
            name="tx-producer",
        ),
        threading.Thread(
            target=run_login_producer,
            args=(producer,),
            daemon=True,
            name="login-producer",
        ),
        threading.Thread(
            target=run_card_producer,
            args=(producer,),
            daemon=True,
            name="card-producer",
        ),
        threading.Thread(
            target=run_noise_alert_producer,
            args=(producer,),
            daemon=True,
            name="alert-producer",
        ),
        threading.Thread(
            target=run_kyc_producer, args=(producer,), daemon=True, name="kyc-producer"
        ),
    ]
    alert_workers = max(1, config.ALERT_WORKERS)
    for idx in range(alert_workers):
        threads.append(
            threading.Thread(
                target=_alert_worker,
                args=(producer,),
                daemon=True,
                name=f"alert-worker-{idx + 1}",
            )
        )

    if config.MINUTE_TICK_ENABLED:
        threads.append(
            threading.Thread(
                target=run_minute_tick_producer,
                args=(producer,),
                daemon=True,
                name="minute-tick",
            )
        )

    for t in threads:
        t.start()
        log.info("Started thread: %s", t.name)

    log.info("All producers running. Press Ctrl+C to stop.")

    while not _stop_event.is_set():
        time.sleep(1)

    for _ in range(alert_workers):
        with contextlib.suppress(queue.Full):
            _alert_queue.put_nowait(_ALERT_SENTINEL)
    with contextlib.suppress(Exception):
        _alert_queue.join()

    log.info("Flushing remaining messages…")
    producer.flush(timeout=10)
    producer.close()
    if health_server is not None:
        health_server.shutdown()
    log.info("Producer shut down cleanly.")


if __name__ == "__main__":
    main()
