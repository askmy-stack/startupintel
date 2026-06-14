"""Tests for the Prometheus metrics endpoint, middleware, and recorders."""

from __future__ import annotations

from fastapi.testclient import TestClient

from startupintel.api.main import app
from startupintel.api.routes.metrics import (
    MetricsMiddleware,
    record_bot_run,
    record_cache_hit,
    record_cache_miss,
    update_circuit_breaker_state,
)

client = TestClient(app)


def test_metrics_endpoint_returns_prometheus_text():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    # Default process/python collectors are always present.
    assert "python_info" in resp.text or "# HELP" in resp.text


def test_recorders_emit_into_registry():
    record_cache_hit("redis")
    record_cache_miss("redis")
    record_bot_run("runway", duration=1.2, success=True)
    record_bot_run("pmf", duration=2.0, success=False)
    update_circuit_breaker_state("groq", "open")

    body = client.get("/metrics").text
    assert 'cache_hits_total{cache_type="redis"}' in body
    assert 'bot_runs_total{bot_name="runway",status="success"}' in body
    assert 'bot_runs_total{bot_name="pmf",status="error"}' in body
    assert 'circuit_breaker_state{service_name="groq"} 1.0' in body


def test_middleware_normalizes_uuid_and_numeric_paths():
    mw = MetricsMiddleware(app)
    uuid_path = "/startup/123e4567-e89b-12d3-a456-426614174000/stress"
    assert mw._normalize_path(uuid_path) == "/startup/{id}/stress"
    assert mw._normalize_path("/investor/42") == "/investor/{id}/"
