"""CRUD route tests against a real async Postgres session."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_startup_crud_roundtrip(client: AsyncClient):
    # create
    resp = await client.post("/startup", json={"name": "Acme", "domain": "acme.io"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Acme"
    startup_id = created["id"]

    # get
    resp = await client.get(f"/startup/{startup_id}")
    assert resp.status_code == 200
    assert resp.json()["domain"] == "acme.io"

    # list
    resp = await client.get("/startup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1

    # delete
    resp = await client.delete(f"/startup/{startup_id}")
    assert resp.status_code == 204
    assert (await client.get(f"/startup/{startup_id}")).status_code == 404


async def test_investor_crud_roundtrip(client: AsyncClient):
    resp = await client.post("/investor", json={"name": "Jane VC", "firm": "Seed Co"})
    assert resp.status_code == 201
    investor_id = resp.json()["id"]

    assert (await client.get(f"/investor/{investor_id}")).status_code == 200
    listing = (await client.get("/investor")).json()
    assert listing["total"] == 1

    assert (await client.delete(f"/investor/{investor_id}")).status_code == 204
    assert (await client.get(f"/investor/{investor_id}")).status_code == 404


async def test_accelerator_crud_roundtrip(client: AsyncClient):
    resp = await client.post(
        "/accelerator", json={"name": "YC", "location": "SF", "cohort_count": 40}
    )
    assert resp.status_code == 201
    accelerator_id = resp.json()["id"]

    fetched = (await client.get(f"/accelerator/{accelerator_id}")).json()
    assert fetched["cohort_count"] == 40

    assert (await client.delete(f"/accelerator/{accelerator_id}")).status_code == 204
    assert (await client.get(f"/accelerator/{accelerator_id}")).status_code == 404


async def test_termsheet_crud_roundtrip(client: AsyncClient):
    resp = await client.post(
        "/termsheet",
        json={
            "raw_text": "2x participating preferred",
            "founder_friendliness_score": 32.5,
            "red_flags": ["participating_preferred"],
        },
    )
    assert resp.status_code == 201
    termsheet_id = resp.json()["id"]
    assert resp.json()["red_flags"] == ["participating_preferred"]

    assert (await client.get(f"/termsheet/{termsheet_id}")).status_code == 200
    assert (await client.get("/termsheet")).json()["total"] == 1

    assert (await client.delete(f"/termsheet/{termsheet_id}")).status_code == 204
    assert (await client.get(f"/termsheet/{termsheet_id}")).status_code == 404


async def test_missing_resource_returns_404(client: AsyncClient):
    missing = "00000000-0000-0000-0000-0000000000ff"
    assert (await client.get(f"/startup/{missing}")).status_code == 404
    assert (await client.get(f"/investor/{missing}")).status_code == 404
    assert (await client.get(f"/accelerator/{missing}")).status_code == 404
    assert (await client.get(f"/termsheet/{missing}")).status_code == 404
