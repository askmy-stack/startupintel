"""Shared FastAPI dependencies.

This module intentionally stays DB-only: a single async session provider and
``get_*_or_404`` helpers used by the CRUD routes. Auth dependencies live in
``startupintel.api.dependencies.auth`` so the CRUD layer can be exercised without
pulling in the auth stack.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.db.models import Accelerator, Investor, Startup
from startupintel.db.postgres import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async for session in get_session():
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


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
