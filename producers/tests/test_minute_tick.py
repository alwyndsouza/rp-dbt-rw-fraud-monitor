"""Tests for the minute-tick producer and liveness probe."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PRODUCERS_DIR = Path(__file__).resolve().parents[1]
if str(PRODUCERS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCERS_DIR))

import main  # noqa: E402


def test_record_publish_updates_metrics_and_timestamp():
    # Reset state
    with main._metrics_lock:
        main._metrics.clear()
    main._last_publish_at = 0.0

    before = time.time()
    main._record_publish("transactions")
    main._record_publish("transactions")
    main._record_publish("login_events")

    assert main._metrics["transactions"] == 2
    assert main._metrics["login_events"] == 1
    assert main._last_publish_at >= before


def test_seconds_until_next_minute_is_in_range():
    result = main._seconds_until_next_minute()
    assert 0.0 < result <= 60.0


def test_minute_tick_emits_batch_and_stops(monkeypatch):
    monkeypatch.setattr(main._stop_event, "set", lambda: None, raising=False)

    # Use a tiny pool so scenarios are reachable quickly.
    import config
    from generators.customer_pool import build_customer_pool

    main.customers = build_customer_pool(10)

    # Shrink batch sizes so the test runs fast.
    monkeypatch.setattr(config, "MINUTE_TICK_TRANSACTIONS", 3)
    monkeypatch.setattr(config, "MINUTE_TICK_LOGINS", 2)

    # Replace the pre-boundary sleep so the tick fires immediately.
    monkeypatch.setattr(main, "_seconds_until_next_minute", lambda: 0.0)

    # Stop after one tick by flipping the stop event inside the first flush.
    fake = MagicMock()

    def stop_after_flush(*_a, **_kw):
        main._stop_event.set()

    fake.flush.side_effect = stop_after_flush

    # Fresh stop_event so the loop actually runs once.
    import threading

    main._stop_event = threading.Event()

    main.run_minute_tick_producer(fake)

    # Expect at least 3 transactions + 2 logins worth of .send() calls.
    topics_sent = [call.args[0] for call in fake.send.call_args_list]
    assert any("transactions" in t for t in topics_sent), topics_sent
    assert any("login_events" in t for t in topics_sent), topics_sent


def test_health_handler_reports_status():
    # Simulate recent publish
    main._last_publish_at = time.time()
    with main._metrics_lock:
        main._metrics.clear()
        main._metrics["transactions"] = 42

    class FakeRequest:
        def makefile(self, *_args, **_kwargs):
            import io

            return io.BytesIO(b"")

    # Build the handler without going through HTTPServer.
    handler = main._HealthHandler.__new__(main._HealthHandler)
    handler.path = "/health"
    handler.wfile = _Capture()
    handler.rfile = _Capture()

    sent_status = {}

    def send_response(code):
        sent_status["code"] = code

    headers = []

    def send_header(k, v):
        headers.append((k, v))

    def end_headers():
        pass

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers

    handler.do_GET()

    assert sent_status["code"] == 200
    body = json.loads(handler.wfile.getvalue().decode())
    assert body["status"] == "ok"
    assert body["published_by_topic"]["transactions"] == 42


def test_health_handler_reports_degraded_when_stale():
    # No publishes ever
    main._last_publish_at = 0.0
    with main._metrics_lock:
        main._metrics.clear()

    handler = main._HealthHandler.__new__(main._HealthHandler)
    handler.path = "/healthz"
    handler.wfile = _Capture()

    captured = {}

    def send_response(code):
        captured["code"] = code

    handler.send_response = send_response
    handler.send_header = lambda *a, **k: None
    handler.end_headers = lambda: None
    handler.do_GET()

    assert captured["code"] == 503


class _Capture:
    """Minimal writable buffer that mimics `wfile`."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def write(self, data: bytes) -> int:
        self._buf.extend(data)
        return len(data)

    def getvalue(self) -> bytes:
        return bytes(self._buf)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
