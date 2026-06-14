"""Integration tests for the bot status/score routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from startupintel.db.models import Startup, StartupScore

pytestmark = pytest.mark.asyncio


async def _seed_startup(db_session, **overrides) -> Startup:
    data = {"name": "TechCorp", "domain": "techcorp.com"}
    data.update(overrides)
    startup = Startup(**data)
    db_session.add(startup)
    await db_session.commit()
    await db_session.refresh(startup)
    return startup


async def _seed_score(db_session, startup_id, bot_name, score, **overrides):
    record = StartupScore(
        startup_id=startup_id,
        bot_name=bot_name,
        score=score,
        computed_at=overrides.get("computed_at", datetime.now(UTC)),
    )
    db_session.add(record)
    await db_session.commit()
    return record


async def test_bot_status_lists_all_bots(client: AsyncClient):
    resp = await client.get("/bot/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_bots"] == 8
    assert body["active_bots"] == 8
    assert body["bots"]["runway"]["status"] == "active"


async def test_invalid_bot_name_400(client: AsyncClient):
    assert (await client.get("/bot/nope/results")).status_code == 400
    assert (await client.get("/bot/nope/stats")).status_code == 400


async def test_bot_results_returns_recent_first(client: AsyncClient, db_session):
    s = await _seed_startup(db_session, name="Alpha", domain="alpha.io")
    now = datetime.now(UTC)
    await _seed_score(db_session, s.id, "runway", 10.0, computed_at=now - timedelta(hours=2))
    await _seed_score(db_session, s.id, "runway", 90.0, computed_at=now)
    await _seed_score(db_session, s.id, "pmf", 50.0)

    resp = await client.get("/bot/runway/results")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["score"] == 90.0
    assert body["items"][0]["status"] == "completed"
    assert all(item["bot_name"] == "runway" for item in body["items"])


async def test_bot_results_respects_limit(client: AsyncClient, db_session):
    s = await _seed_startup(db_session, name="Beta", domain="beta.io")
    for i in range(5):
        await _seed_score(
            db_session, s.id, "pmf", float(i), computed_at=datetime.now(UTC) + timedelta(seconds=i)
        )
    resp = await client.get("/bot/pmf/results", params={"limit": 2})
    assert resp.json()["total"] == 2


async def test_bot_stats_aggregates(client: AsyncClient, db_session):
    s = await _seed_startup(db_session, name="Gamma", domain="gamma.io")
    await _seed_score(db_session, s.id, "acqui", 20.0)
    await _seed_score(db_session, s.id, "acqui", 80.0)

    body = (await client.get("/bot/acqui/stats")).json()
    assert body["bot_name"] == "acqui"
    assert body["total_analyses"] == 2
    assert body["average_score"] == 50.0
    assert body["min_score"] == 20.0
    assert body["max_score"] == 80.0


async def test_bot_stats_empty(client: AsyncClient):
    body = (await client.get("/bot/pivot/stats")).json()
    assert body["total_analyses"] == 0
    assert body["average_score"] == 0


async def test_recent_scores_across_bots(client: AsyncClient, db_session):
    s = await _seed_startup(db_session, name="Delta", domain="delta.io")
    await _seed_score(db_session, s.id, "runway", 30.0)
    await _seed_score(db_session, s.id, "pmf", 70.0)

    body = (await client.get("/bot/scores/recent")).json()
    assert len(body) == 2
    assert {row["bot_name"] for row in body} == {"runway", "pmf"}
