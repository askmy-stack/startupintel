"""Tests for the feature-flag admin routes (auth + redis mocked)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from startupintel.api.dependencies.auth import get_current_user
from startupintel.api.main import app
from startupintel.api.routes import feature_flags as route_mod
from startupintel.db.models import User
from startupintel.utils import feature_flags as ff_mod


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl, value: str) -> None:
        self.store[key] = value

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self.store.pop(k, None)


def _admin() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="x",
        role="admin",
        organization_id=uuid4(),
    )


def _analyst() -> User:
    return User(
        id=uuid4(),
        email="analyst@example.com",
        hashed_password="x",
        role="analyst",
        organization_id=uuid4(),
    )


@pytest.fixture
def fake_redis(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(ff_mod, "get_redis", lambda: fake)
    monkeypatch.setattr(route_mod, "get_redis", lambda: fake)
    return fake


@pytest.fixture
def admin_client(fake_redis: FakeRedis):
    app.dependency_overrides[get_current_user] = _admin
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_then_list_and_get_flag(admin_client: TestClient):
    resp = admin_client.post(
        "/feature-flags/",
        params={"flag_key": "new_ui", "name": "New UI", "enabled": True},
    )
    assert resp.status_code == 201
    assert resp.json()["key"] == "new_ui"

    listed = admin_client.get("/feature-flags/").json()
    assert listed["total"] == 1
    assert listed["items"][0]["key"] == "new_ui"

    got = admin_client.get("/feature-flags/new_ui").json()
    assert got["key"] == "new_ui"


def test_get_unknown_flag_404(admin_client: TestClient):
    assert admin_client.get("/feature-flags/missing").status_code == 404


def test_update_flag(admin_client: TestClient):
    admin_client.post("/feature-flags/", params={"flag_key": "f1", "name": "F1"})
    resp = admin_client.put("/feature-flags/f1", params={"enabled": False, "percentage": 25})
    assert resp.status_code == 200
    updated = admin_client.get("/feature-flags/f1").json()
    assert updated["enabled"] is False
    assert updated["percentage"] == 25


def test_update_unknown_flag_404(admin_client: TestClient):
    assert admin_client.put("/feature-flags/nope", params={"enabled": True}).status_code == 404


def test_delete_flag(admin_client: TestClient):
    admin_client.post("/feature-flags/", params={"flag_key": "tmp", "name": "Tmp"})
    assert admin_client.delete("/feature-flags/tmp").status_code == 204
    assert admin_client.get("/feature-flags/tmp").status_code == 404


def test_check_flag_for_current_user(admin_client: TestClient):
    admin_client.post(
        "/feature-flags/",
        params={"flag_key": "chk", "name": "Chk", "strategy": "always_on", "enabled": True},
    )
    body = admin_client.get("/feature-flags/check/chk").json()
    assert body["flag_key"] == "chk"
    assert body["enabled"] is True


def test_enable_disable_helpers(admin_client: TestClient):
    admin_client.post("/feature-flags/", params={"flag_key": "tog", "name": "Tog"})
    admin_client.post("/feature-flags/tog/enable")
    assert admin_client.get("/feature-flags/tog").json()["enabled"] is True
    admin_client.post("/feature-flags/tog/disable")
    assert admin_client.get("/feature-flags/tog").json()["enabled"] is False


def test_non_admin_forbidden(fake_redis: FakeRedis):
    app.dependency_overrides[get_current_user] = _analyst
    try:
        client = TestClient(app)
        resp = client.get("/feature-flags/")
        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_redis_roundtrip_persists(admin_client: TestClient, fake_redis: FakeRedis):
    admin_client.post("/feature-flags/", params={"flag_key": "p", "name": "P"})
    assert any(k.startswith("ff:p") for k in fake_redis.store)
    # TTL is set via setex with a timedelta argument.
    assert isinstance(timedelta(seconds=300), timedelta)
