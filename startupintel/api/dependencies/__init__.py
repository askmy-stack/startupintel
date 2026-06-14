"""Shared FastAPI dependencies.

This module stays auth-free: a single async session provider, the
``get_*_or_404`` CRUD helpers, and lightweight Redis/LLM/rate-limit providers.
Auth dependencies live in ``startupintel.api.dependencies.auth`` so the CRUD
layer can be exercised without pulling in the auth stack.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.db.models import Accelerator, Investor, Startup
from startupintel.db.postgres import get_session
from startupintel.db.redis import get_redis
from startupintel.llm.client import get_llm_client

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from startupintel.llm.client import BaseLLMClient

__all__ = [
    "DbDep",
    "RateLimiter",
    "get_accelerator_or_404",
    "get_db",
    "get_investor_or_404",
    "get_llm",
    "get_llm_client",
    "get_redis_client",
    "get_startup_or_404",
    "rate_limit_dependency",
]


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async for session in get_session():
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_redis_client() -> "Redis":
    """Provide a Redis client for routes that need a cache/session store."""
    return get_redis()


async def get_llm() -> "BaseLLMClient":
    """Provide the configured LLM client."""
    return get_llm_client()


async def get_startup_or_404(db: DbDep, startup_id: UUID) -> Startup:
    startup = await db.get(Startup, startup_id)
    if startup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup {startup_id} not found",
        )
    return startup


async def get_investor_or_404(db: DbDep, investor_id: UUID) -> Investor:
    investor = await db.get(Investor, investor_id)
    if investor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investor {investor_id} not found",
        )
    return investor


async def get_accelerator_or_404(db: DbDep, accelerator_id: UUID) -> Accelerator:
    accelerator = await db.get(Accelerator, accelerator_id)
    if accelerator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accelerator {accelerator_id} not found",
        )
    return accelerator


# Simple in-process rate limiter. For distributed deployments, back this with
# Redis; the in-memory window is sufficient for single-instance/dev use.
_rate_limit_store: dict[str, list[datetime]] = {}


class RateLimiter:
    """Fixed-window-per-key in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window = timedelta(minutes=1)

    def check(self, key: str) -> tuple[bool, int, int]:
        """Return ``(allowed, remaining, reset_in_seconds)`` for ``key``."""
        now = datetime.now(UTC)
        cutoff = now - self.window
        recent = [ts for ts in _rate_limit_store.get(key, []) if ts > cutoff]

        if len(recent) >= self.requests_per_minute:
            reset_in = int((recent[0] + self.window - now).total_seconds())
            _rate_limit_store[key] = recent
            return False, 0, max(reset_in, 1)

        recent.append(now)
        _rate_limit_store[key] = recent
        return True, self.requests_per_minute - len(recent), 60


async def rate_limit_dependency(
    request: Request,
    requests_per_minute: int = 60,
) -> None:
    """FastAPI dependency enforcing a per-client-IP, per-path rate limit."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"

    allowed, remaining, reset_in = RateLimiter(requests_per_minute).check(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
            headers={
                "X-RateLimit-Limit": str(requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_in),
                "Retry-After": str(reset_in),
            },
        )

    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_limit = requests_per_minute
