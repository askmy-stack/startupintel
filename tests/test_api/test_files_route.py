"""Integration tests for the file upload/management routes."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from startupintel.api.dependencies.auth import get_current_user
from startupintel.api.main import app
from startupintel.api.routes import files as files_mod
from startupintel.db.models import Organization, User
from startupintel.utils.storage import LocalStorageBackend

pytestmark = pytest.mark.asyncio


async def _seed_user(db_session, org_id, role: str = "analyst") -> User:
    user = User(
        email=f"{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        role=role,
        organization_id=org_id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_org(db_session) -> Organization:
    org = Organization(name="Acme", slug=f"acme-{uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def files_client(db_session, tmp_path):
    org = await _seed_org(db_session)
    user = await _seed_user(db_session, org.id)

    async def _override_get_db():
        yield db_session

    backend = LocalStorageBackend(str(tmp_path))
    original_backend = files_mod.get_storage_backend
    files_mod.get_storage_backend = lambda: backend

    from startupintel.api.dependencies import get_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, user, org
    app.dependency_overrides.clear()
    files_mod.get_storage_backend = original_backend


def _upload(ac, content=b"hello world", filename="note.txt", **form):
    data = {"category": "document", **form}
    files = {"file": (filename, content, "text/plain")}
    return ac.post("/files/upload", data=data, files=files)


async def test_upload_then_download(files_client):
    ac, _, _ = files_client
    resp = await _upload(ac, content=b"the contents")
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "note.txt"
    assert body["virus_scan_status"] == "clean"
    file_id = body["id"]

    dl = await ac.get(f"/files/{file_id}/download")
    assert dl.status_code == 200
    assert dl.content == b"the contents"
    assert "attachment" in dl.headers["content-disposition"]


async def test_upload_rejects_bad_category(files_client):
    ac, _, _ = files_client
    resp = await _upload(ac, category="malware")
    assert resp.status_code == 400


async def test_upload_rejects_disallowed_extension(files_client):
    ac, _, _ = files_client
    resp = await _upload(ac, filename="evil.exe")
    assert resp.status_code == 415


async def test_upload_rejects_too_large(files_client, monkeypatch):
    ac, _, _ = files_client
    monkeypatch.setattr(files_mod.get_settings(), "max_upload_size_mb", 0)
    resp = await _upload(ac, content=b"x" * 1024)
    assert resp.status_code == 413


async def test_list_files_paginates_and_filters(files_client):
    ac, _, _ = files_client
    await _upload(ac, filename="a.txt", category="document")
    await _upload(ac, filename="b.txt", category="report")

    listing = (await ac.get("/files/")).json()
    assert listing["total"] == 2
    assert listing["total_pages"] == 1

    filtered = (await ac.get("/files/", params={"category": "report"})).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["category"] == "report"


async def test_download_unknown_404(files_client):
    ac, _, _ = files_client
    assert (await ac.get(f"/files/{uuid4()}/download")).status_code == 404


async def test_delete_soft_deletes(files_client):
    ac, _, _ = files_client
    file_id = (await _upload(ac)).json()["id"]

    assert (await ac.delete(f"/files/{file_id}")).status_code == 204
    assert (await ac.get("/files/")).json()["total"] == 0
    assert (await ac.get(f"/files/{file_id}/download")).status_code == 404


async def test_delete_forbidden_for_non_owner(files_client, db_session):
    ac, _, org = files_client
    file_id = (await _upload(ac)).json()["id"]

    # A different non-admin user in the SAME org can see but not delete the file.
    other = await _seed_user(db_session, org.id, role="analyst")
    app.dependency_overrides[get_current_user] = lambda: other
    assert (await ac.delete(f"/files/{file_id}")).status_code == 403


async def test_delete_allowed_for_admin(files_client, db_session):
    ac, _, org = files_client
    file_id = (await _upload(ac)).json()["id"]

    admin = await _seed_user(db_session, org.id, role="admin")
    app.dependency_overrides[get_current_user] = lambda: admin
    assert (await ac.delete(f"/files/{file_id}")).status_code == 204
