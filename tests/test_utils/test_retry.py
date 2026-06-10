"""Tests for the tenacity-based retry utilities."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from startupintel.utils.retry import (
    DB_RETRY_EXCEPTIONS,
    db_retry,
    execute_with_retry,
)

pytestmark = pytest.mark.asyncio


async def test_db_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    @db_retry(max_attempts=3, min_wait=0.0, max_wait=0.0)
    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("stmt", {}, Exception("boom"))
        return "ok"

    assert await flaky() == "ok"
    assert calls["n"] == 3


async def test_db_retry_reraises_after_exhausting_attempts():
    calls = {"n": 0}

    @db_retry(max_attempts=2, min_wait=0.0, max_wait=0.0)
    async def always_fails() -> None:
        calls["n"] += 1
        raise OperationalError("stmt", {}, Exception("boom"))

    with pytest.raises(OperationalError):
        await always_fails()
    assert calls["n"] == 2


async def test_db_retry_does_not_retry_unlisted_exception():
    calls = {"n": 0}

    @db_retry(max_attempts=3, min_wait=0.0, max_wait=0.0)
    async def raises_value_error() -> None:
        calls["n"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        await raises_value_error()
    assert calls["n"] == 1


async def test_execute_with_retry_runs_callable():
    async def add(a: int, b: int) -> int:
        return a + b

    assert await execute_with_retry(add, 2, 3) == 5
    assert OperationalError in DB_RETRY_EXCEPTIONS
