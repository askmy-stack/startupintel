"""Tests for serving the static dashboard UI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from startupintel.api.main import create_app


def test_root_serves_dashboard_html():
    client = TestClient(create_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<!DOCTYPE html>" in resp.text
    assert "StartupIntel" in resp.text


def test_static_index_is_mounted():
    client = TestClient(create_app())
    resp = client.get("/static/index.html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
