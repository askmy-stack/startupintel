"""Integration tests for the auth API (register → verify → login → refresh → me → logout)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(
    client: AsyncClient, *, email: str = "alice@example.com", password: str = "str0ngP@ss"
) -> dict:
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Alice",
            "last_name": "Tester",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _verify(client: AsyncClient, token: str) -> dict:
    resp = await client.post("/auth/verify-email", json={"token": token})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _register_and_verify(
    client: AsyncClient, *, email: str = "alice@example.com", password: str = "str0ngP@ss"
) -> dict:
    user = await _register(client, email=email, password=password)
    return await _verify(client, user["verification_token"])


async def _login(
    client: AsyncClient, *, email: str = "alice@example.com", password: str = "str0ngP@ss"
) -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_register_creates_inactive_unverified_user(client: AsyncClient):
    user = await _register(client)
    assert user["email"] == "alice@example.com"
    assert user["role"] == "admin"
    assert user["organization_id"] is not None
    assert user["is_active"] is False
    assert user["email_verified"] is False
    assert user["verification_token"]


async def test_register_duplicate_email_rejects(client: AsyncClient):
    await _register(client)
    resp = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "str0ngP@ss"},
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_login_before_verify_forbidden(client: AsyncClient):
    await _register(client)
    resp = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "str0ngP@ss"},
    )
    assert resp.status_code == 403


async def test_verify_then_login_returns_tokens(client: AsyncClient):
    await _register_and_verify(client)
    tokens = await _login(client)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["user"]["email"] == "alice@example.com"
    assert tokens["user"]["email_verified"] is True
    assert tokens["user"]["is_active"] is True


async def test_login_wrong_password_rejects(client: AsyncClient):
    await _register_and_verify(client)
    resp = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_refresh_rotates_token(client: AsyncClient):
    await _register_and_verify(client)
    tokens = await _login(client)

    resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


async def test_me_requires_bearer(client: AsyncClient):
    await _register_and_verify(client)
    tokens = await _login(client)
    resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


async def test_logout_revokes_refresh(client: AsyncClient):
    await _register_and_verify(client)
    tokens = await _login(client)
    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401
