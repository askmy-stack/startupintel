"""Tests for the feature-flag system (pure logic + redis-mocked round-trips)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from startupintel.utils import feature_flags as ff_mod
from startupintel.utils.feature_flags import (
    FeatureFlag,
    FeatureFlagCondition,
    FeatureFlagManager,
    FeatureFlagOperator,
    FeatureFlagStrategy,
)


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


@pytest.fixture
def manager(monkeypatch) -> FeatureFlagManager:
    fake = FakeRedis()
    monkeypatch.setattr(ff_mod, "get_redis", lambda: fake)
    return FeatureFlagManager()


# ---------- pure logic ----------


def test_evaluate_condition_operators():
    mgr = FeatureFlagManager()
    ctx = {"user": {"role": "admin", "email": "a@example.com", "age": 30}}

    def cond(op, value, attr="user.role"):
        return mgr._evaluate_condition(
            FeatureFlagCondition(attribute=attr, operator=op, value=value), ctx
        )

    assert cond(FeatureFlagOperator.EQUALS, "admin")
    assert not cond(FeatureFlagOperator.EQUALS, "viewer")
    assert cond(FeatureFlagOperator.NOT_EQUALS, "viewer")
    assert cond(FeatureFlagOperator.IN, ["admin", "analyst"])
    assert cond(FeatureFlagOperator.NOT_IN, ["viewer"])
    assert cond(FeatureFlagOperator.GREATER_THAN, 18, attr="user.age")
    assert cond(FeatureFlagOperator.LESS_THAN, 40, attr="user.age")
    assert cond(FeatureFlagOperator.CONTAINS, "example", attr="user.email")
    assert cond(FeatureFlagOperator.STARTS_WITH, "a@", attr="user.email")
    assert cond(FeatureFlagOperator.ENDS_WITH, ".com", attr="user.email")


def test_evaluate_condition_missing_attribute_is_false():
    mgr = FeatureFlagManager()
    cond = FeatureFlagCondition(
        attribute="user.nonexistent",
        operator=FeatureFlagOperator.EQUALS,
        value="x",
    )
    assert mgr._evaluate_condition(cond, {"user": {}}) is False


def test_evaluate_conditions_and_logic():
    mgr = FeatureFlagManager()
    ctx = {"plan": "pro", "seats": 5}
    conds = [
        FeatureFlagCondition("plan", FeatureFlagOperator.EQUALS, "pro"),
        FeatureFlagCondition("seats", FeatureFlagOperator.GREATER_THAN, 3),
    ]
    assert mgr._evaluate_conditions(conds, ctx) is True
    conds.append(FeatureFlagCondition("seats", FeatureFlagOperator.LESS_THAN, 4))
    assert mgr._evaluate_conditions(conds, ctx) is False
    assert mgr._evaluate_conditions([], ctx) is True


def test_hash_for_percentage_is_deterministic_and_bounded():
    mgr = FeatureFlagManager()
    a = mgr._hash_for_percentage("user-123", "flagx")
    b = mgr._hash_for_percentage("user-123", "flagx")
    assert a == b
    assert 0 <= a < 100


def test_flag_dict_roundtrip():
    mgr = FeatureFlagManager()
    flag = FeatureFlag(
        key="new_ui",
        name="New UI",
        description="rollout",
        strategy=FeatureFlagStrategy.PERCENTAGE,
        percentage=50,
        conditions=[FeatureFlagCondition("plan", FeatureFlagOperator.EQUALS, "pro")],
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    restored = mgr._dict_to_flag(mgr._flag_to_dict(flag))
    assert restored.key == "new_ui"
    assert restored.strategy is FeatureFlagStrategy.PERCENTAGE
    assert restored.percentage == 50
    assert restored.conditions[0].operator is FeatureFlagOperator.EQUALS


# ---------- redis-backed ----------


async def test_is_enabled_default_when_missing(manager: FeatureFlagManager):
    assert await manager.is_enabled("absent", default=True) is True
    assert await manager.is_enabled("absent", default=False) is False


async def test_create_then_is_enabled_always_on(manager: FeatureFlagManager):
    await manager.create_flag(FeatureFlag(
        key="beta",
        name="Beta",
        description="",
        strategy=FeatureFlagStrategy.ALWAYS_ON,
    ))
    assert await manager.is_enabled("beta") is True


async def test_globally_disabled_flag_returns_false(manager: FeatureFlagManager):
    await manager.create_flag(FeatureFlag(
        key="off",
        name="Off",
        description="",
        strategy=FeatureFlagStrategy.ALWAYS_ON,
        enabled=False,
    ))
    assert await manager.is_enabled("off") is False


async def test_expired_flag_returns_default(manager: FeatureFlagManager):
    await manager.create_flag(FeatureFlag(
        key="old",
        name="Old",
        description="",
        strategy=FeatureFlagStrategy.ALWAYS_ON,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    ))
    assert await manager.is_enabled("old", default=False) is False


async def test_delete_flag(manager: FeatureFlagManager):
    await manager.create_flag(FeatureFlag(
        key="tmp", name="Tmp", description="", strategy=FeatureFlagStrategy.ALWAYS_ON,
    ))
    assert await manager.is_enabled("tmp") is True
    assert await manager.delete_flag("tmp") is True
    assert await manager.is_enabled("tmp", default=False) is False
