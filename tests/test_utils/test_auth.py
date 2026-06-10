"""Tests for authentication utilities (password hashing, JWT, API keys)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from startupintel.utils.auth import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_password_hash,
    verify_api_key,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_encodes_claims_and_decodes():
    user_id, org_id = uuid4(), uuid4()
    token, jti = create_access_token(user_id, org_id, role="admin")

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["org"] == str(org_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert payload["jti"] == str(jti)


def test_refresh_token_returns_storable_hash():
    user_id = uuid4()
    token, token_hash = create_refresh_token(user_id)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    # hash is deterministic sha256 hex of the token, safe to persist
    assert len(token_hash) == 64
    assert token_hash != token


def test_decode_token_rejects_garbage():
    assert decode_token("not-a-jwt") is None


def test_decode_token_rejects_expired():
    token, _ = create_access_token(
        uuid4(), uuid4(), role="viewer", expires_delta=timedelta(seconds=-1)
    )
    assert decode_token(token) is None


def test_generate_and_verify_api_key():
    full_key, prefix, key_hash = generate_api_key()
    assert full_key.startswith("si_")
    assert prefix == full_key[:8]
    assert len(key_hash) == 64
    assert verify_api_key(full_key, key_hash) is True
    assert verify_api_key("si_tampered", key_hash) is False


def test_password_reset_token_is_typed():
    user_id = uuid4()
    payload = decode_token(create_password_reset_token(user_id))
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "password_reset"
