"""Tests for the circuit breaker."""

from __future__ import annotations

import pytest

from startupintel.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    circuit_breaker,
)


def _breaker(name: str, **cfg) -> CircuitBreaker:
    return CircuitBreaker(name, CircuitBreakerConfig(**cfg))


@pytest.mark.asyncio
async def test_successful_call_passes_through():
    breaker = _breaker("cb-success")

    async def ok() -> str:
        return "ok"

    assert await breaker.call(ok) == "ok"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold_failures():
    breaker = _breaker("cb-open", failure_threshold=2)

    async def boom() -> None:
        raise RuntimeError("fail")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(boom)

    assert breaker.state is CircuitState.OPEN

    # While OPEN, calls are rejected without invoking the function.
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(boom)


@pytest.mark.asyncio
async def test_recovers_to_closed_after_timeout():
    breaker = _breaker(
        "cb-recover",
        failure_threshold=1,
        recovery_timeout=0.0,
        success_threshold=1,
    )

    async def boom() -> None:
        raise RuntimeError("fail")

    async def ok() -> str:
        return "ok"

    with pytest.raises(RuntimeError):
        await breaker.call(boom)
    assert breaker.state is CircuitState.OPEN

    # recovery_timeout=0 -> next call transitions to HALF_OPEN then CLOSED on success
    assert await breaker.call(ok) == "ok"
    assert breaker.state is CircuitState.CLOSED


def test_registry_returns_named_singletons():
    a = circuit_breaker("cb-registry-unique")
    b = circuit_breaker("cb-registry-unique")
    assert a is b
    # Pre-configured breakers are available by name.
    assert circuit_breaker("groq").name == "groq"
