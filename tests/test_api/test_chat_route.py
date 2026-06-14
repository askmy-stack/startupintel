"""Tests for the chat routes and the shared rate-limit dependency."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from startupintel.api import dependencies as deps
from startupintel.api.dependencies import RateLimiter
from startupintel.api.main import app
from startupintel.api.routes import chat as chat_mod


class FakeLLM:
    async def complete(self, prompt: str, **kwargs) -> str:
        return "Here is a concise, data-driven answer."


class FailingLLM:
    async def complete(self, prompt: str, **kwargs) -> str:
        raise RuntimeError("llm down")


class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class FakeSession:
    async def execute(self, *args, **kwargs):
        return _EmptyResult()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(chat_mod, "get_llm_client", lambda: FakeLLM())

    async def _no_redis():
        return None

    async def _fake_db():
        yield FakeSession()

    app.dependency_overrides[deps.get_redis_client] = _no_redis
    app.dependency_overrides[deps.get_db] = _fake_db
    chat_mod._conversations.clear()
    deps._rate_limit_store.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_send_returns_response_and_conversation_id(client: TestClient):
    resp = client.post("/chat/send", json={"message": "How is my runway?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    assert body["message"]["metadata"]["intent"] == "runway_analysis"
    assert body["suggested_actions"]


def test_send_sanitizes_html(client: TestClient):
    resp = client.post("/chat/send", json={"message": "<script>alert(1)</script> hello"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]
    history = client.get(f"/chat/conversations/{cid}/history").json()
    assert "<script>" not in history[0]["content"]
    assert "hello" in history[0]["content"]


def test_send_rejects_empty_message(client: TestClient):
    resp = client.post("/chat/send", json={"message": "   "})
    assert resp.status_code == 400


def test_send_rejects_too_long_message(client: TestClient):
    resp = client.post("/chat/send", json={"message": "a" * 4001})
    assert resp.status_code == 400


def test_conversation_is_continued(client: TestClient):
    first = client.post("/chat/send", json={"message": "hello"}).json()
    cid = first["conversation_id"]
    client.post("/chat/send", json={"message": "and again", "conversation_id": cid})
    history = client.get(f"/chat/conversations/{cid}/history").json()
    # 2 user + 2 assistant messages.
    assert len(history) == 4


def test_clear_conversation(client: TestClient):
    cid = client.post("/chat/send", json={"message": "hello"}).json()["conversation_id"]
    assert client.post(f"/chat/conversations/{cid}/clear").status_code == 200
    assert client.get(f"/chat/conversations/{cid}/history").json() == []


def test_history_unknown_conversation_404(client: TestClient):
    assert client.get("/chat/conversations/nope/history").status_code == 404
    assert client.post("/chat/conversations/nope/clear").status_code == 404


def test_llm_failure_falls_back_gracefully(client: TestClient, monkeypatch):
    monkeypatch.setattr(chat_mod, "get_llm_client", lambda: FailingLLM())
    resp = client.post("/chat/send", json={"message": "how is pmf?"})
    assert resp.status_code == 200
    assert "startup" in resp.json()["message"]["content"].lower()


def test_stream_emits_sse_events(client: TestClient):
    resp = client.post("/chat/stream", json={"message": "runway please"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    types = [
        json.loads(line[len("data: ") :])["type"]
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    assert types[0] == "conversation_id"
    assert "complete" in types


def test_intents_endpoint(client: TestClient):
    body = client.get("/chat/intents").json()
    assert "runway_analysis" in body
    assert body["general"]


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(requests_per_minute=2)
    assert limiter.check("k")[0] is True
    assert limiter.check("k")[0] is True
    allowed, remaining, reset_in = limiter.check("k")
    assert allowed is False
    assert remaining == 0
    assert reset_in >= 1
