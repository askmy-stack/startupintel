"""Integration tests for the export routes (CSV/JSON streaming)."""

from __future__ import annotations

import csv
import io
import json

import pytest
from httpx import AsyncClient

from startupintel.db.models import Startup

pytestmark = pytest.mark.asyncio


async def _seed_startup(db_session, **overrides) -> Startup:
    data = {
        "name": "TechCorp",
        "domain": "techcorp.com",
        "industry": "Software",
        "stage": "series_a",
    }
    data.update(overrides)
    startup = Startup(**data)
    db_session.add(startup)
    await db_session.commit()
    await db_session.refresh(startup)
    return startup


async def test_export_startups_csv(client: AsyncClient, db_session):
    await _seed_startup(db_session, name="Alpha", domain="alpha.io")

    resp = await client.get("/export/startups/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in resp.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0][:3] == ["id", "name", "domain"]
    assert any(r[1] == "Alpha" for r in rows[1:])


async def test_export_startups_json(client: AsyncClient, db_session):
    await _seed_startup(db_session, name="Beta", domain="beta.io")

    resp = await client.get("/export/startups/json")
    assert resp.status_code == 200
    payload = json.loads(resp.text)
    assert payload["count"] >= 1
    assert any(s["name"] == "Beta" for s in payload["startups"])


async def test_export_startups_csv_filters_by_stage(client: AsyncClient, db_session):
    await _seed_startup(db_session, name="Seedy", domain="seedy.io", stage="seed")
    await _seed_startup(db_session, name="Growthy", domain="growthy.io", stage="growth")

    resp = await client.get("/export/startups/csv", params={"stage": "seed"})
    assert resp.status_code == 200
    names = [r[1] for r in csv.reader(io.StringIO(resp.text))][1:]
    assert "Seedy" in names
    assert "Growthy" not in names


async def test_export_single_startup_report_json(client: AsyncClient, db_session):
    startup = await _seed_startup(db_session, name="Reportly", domain="reportly.io")

    resp = await client.get(f"/export/startup/{startup.id}/report", params={"format": "json"})
    assert resp.status_code == 200
    report = json.loads(resp.text)
    assert report["startup"]["name"] == "Reportly"
    assert report["scores"] == []


async def test_export_report_404_for_unknown_startup(client: AsyncClient):
    from uuid import uuid4

    resp = await client.get(f"/export/startup/{uuid4()}/report")
    assert resp.status_code == 404


async def test_import_template_download(client: AsyncClient):
    resp = await client.get("/export/startups/template")
    assert resp.status_code == 200
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0][0] == "name"
    assert rows[1][0] == "TechCorp"
