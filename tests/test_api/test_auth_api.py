"""Integration tests for the auth API (register → login → refresh → me → logout)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, *, email: str = "alice@example.com", password: str = "str0ngP@ss") -> dict:
    resp = await client.post("/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Alice",
        "last_name": "Tester",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client: AsyncClient, *, email: str = "alice@example.com", password: str = "str0ngP@ss") -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_register_creates_user_and_org(client: AsyncClient):
    user = await _register(client)
    assert user["email"] == "alice@example.com"
    assert user["role"] == "admin"
    assert user["organization_id"] is not None


async def test_register_duplicate_email_rejects(client: AsyncClient):
    await _register(client)
    resp = await client.post("/auth/register", json={
        "email": "alice@example.com",
        "password": "str0ngP@ss",
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_login_returns_tokens(client: AsyncClient):
    await _register(client)
    tokens = await _login(client)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["user"]["email"] == "alice@example.com"


async def test_login_wrong_password_rejects(client: AsyncClient):
    await _register(client)
    resp = await client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


async def test_refresh_rotates_token(client: AsyncClient):
    await _register(client)
    tokens = await _login(client)

    resp = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


async def test_refresh_revoked_token_rejects(client: AsyncClient):
    await _register(client)
    tokens = await _login(client)

    # first refresh succeeds, revoking the old token
    await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    # second refresh with same (now-revoked) token fails
    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


async def test_refresh_expired_token_rejects(client: AsyncClient, db_session):
    """Expired refresh tokens must not rotate into a new pair (#41)."""
    from datetime import UTC, datetime, timedelta
    import hashlib

    from sqlalchemy import select

    from startupintel.db.models import RefreshToken

    await _register(client)
    tokens = await _login(client)
    token_hash = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


async def test_me_returns_profile(client: AsyncClient):
    await _register(client)
    tokens = await _login(client)

    resp = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


async def test_me_rejects_without_token(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_logout_revokes_token(client: AsyncClient):
    await _register(client)
    tokens = await _login(client)

    resp = await client.post("/auth/logout", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 200
    assert "logged out" in resp.json()["message"].lower()

    # revoked token should fail on refresh
    resp = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 401
