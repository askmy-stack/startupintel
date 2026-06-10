"""Shared pytest fixtures.

The DB fixtures below are opt-in: only tests that request ``client`` or
``db_session`` spin up a Postgres-backed schema, so the dependency-light unit
tests keep running without a database. Set ``POSTGRES_URL`` to point at the test
database (defaults to the value in ``config.py``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from startupintel.api.dependencies import get_db
from startupintel.api.main import app
from startupintel.config import get_settings
from startupintel.db.models import Base


@pytest_asyncio.fixture
async def engine() -> AsyncIterator:
    eng = create_async_engine(get_settings().postgres_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
