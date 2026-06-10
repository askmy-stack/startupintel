"""Tests for the WebSocket routes (chat + bot-stream + demo page)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from startupintel.api.main import app

client = TestClient(app)


def test_ws_ping_pong():
    with client.websocket_connect("/ws/chat/c1") as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


def test_ws_chat_streams_chunks_then_complete():
    with client.websocket_connect("/ws/chat/c2") as ws:
        ws.send_json({"type": "message", "content": "hello there", "conversation_id": "x"})

        typing = ws.receive_json()
        assert typing["type"] == "typing"
        assert typing["conversation_id"] == "x"

        chunks = []
        msg = ws.receive_json()
        while msg["type"] == "chunk":
            chunks.append(msg["content"])
            msg = ws.receive_json()

        assert chunks, "expected at least one streamed chunk"
        assert msg["type"] == "complete"
        assert msg["conversation_id"] == "x"
        assert isinstance(msg["suggested_actions"], list)


def test_ws_invalid_json_returns_error():
    with client.websocket_connect("/ws/chat/c3") as ws:
        ws.send_text("not json")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "Invalid JSON" in err["message"]


def test_ws_unknown_type_returns_error():
    with client.websocket_connect("/ws/chat/c4") as ws:
        ws.send_json({"type": "bogus"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "Unknown message type" in err["message"]


def test_ws_bot_stream_progress_then_complete():
    with client.websocket_connect("/ws/bot-stream/s1") as ws:
        ws.send_json({"bot_name": "runway", "action": "start"})

        status = ws.receive_json()
        assert status["type"] == "status"
        assert status["bot_name"] == "runway"

        progresses = []
        msg = ws.receive_json()
        while msg["type"] == "progress":
            progresses.append(msg["progress"])
            msg = ws.receive_json()

        assert progresses[-1] == 100
        assert msg["type"] == "complete"
        assert msg["startup_id"] == "s1"


def test_ws_demo_page_served():
    resp = client.get("/ws/demo")
    assert resp.status_code == 200
    assert "WebSocket Chat Demo" in resp.text
