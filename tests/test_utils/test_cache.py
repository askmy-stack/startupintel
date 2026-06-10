"""Tests for the redis-backed cache utilities (redis mocked in-memory)."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from startupintel.utils import cache as cache_mod
from startupintel.utils.cache import CacheManager

pytestmark = pytest.mark.asyncio


class FakeRedis:
    """Minimal async Redis stand-in supporting the calls cache.py makes."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl, value: str) -> None:
        assert isinstance(ttl, timedelta)
        self.store[key] = value

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self.store.pop(k, None)


@pytest.fixture
def fake_redis(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(cache_mod, "get_redis", lambda: fake)
    return fake


async def test_set_then_get_roundtrip(fake_redis: FakeRedis):
    mgr = CacheManager()
    await mgr.set("k1", {"a": 1, "b": [2, 3]})
    assert await mgr.get("k1") == {"a": 1, "b": [2, 3]}


async def test_get_missing_returns_none(fake_redis: FakeRedis):
    assert await CacheManager().get("nope") is None


async def test_set_uses_cache_prefix(fake_redis: FakeRedis):
    await CacheManager().set("foo", 42)
    assert "cache:foo" in fake_redis.store
    assert json.loads(fake_redis.store["cache:foo"]) == 42


async def test_delete_by_pattern(fake_redis: FakeRedis):
    mgr = CacheManager()
    await mgr.set("startups:1", 1)
    await mgr.set("startups:2", 2)
    await mgr.set("investors:1", 3)

    await mgr.delete("startups:")
    assert await mgr.get("startups:1") is None
    assert await mgr.get("startups:2") is None
    assert await mgr.get("investors:1") == 3


async def test_invalidate_prefix(fake_redis: FakeRedis):
    mgr = CacheManager()
    await mgr.set("bots:abc", 1)
    await mgr.invalidate_prefix("bots")
    assert await mgr.get("bots:abc") is None


async def test_get_swallows_redis_errors(monkeypatch):
    def boom() -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr(cache_mod, "get_redis", boom)
    # Errors are logged and swallowed, returning None rather than raising.
    assert await CacheManager().get("k") is None
