"""Tests for the notification system (console fallbacks + mocked transports)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from startupintel.utils import notifications as notif_mod
from startupintel.utils.notifications import (
    EmailNotifier,
    Notification,
    NotificationChannel,
    NotificationManager,
    NotificationPriority,
    SlackNotifier,
    WebhookNotifier,
)

pytestmark = pytest.mark.asyncio


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeAsyncClient:
    """Async context manager whose .post returns a queued FakeResponse."""

    last_call: dict = {}

    def __init__(self, response: FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        FakeAsyncClient.last_call = {"url": url, **kwargs}
        return self._response


def _patch_client(monkeypatch, response: FakeResponse):
    monkeypatch.setattr(
        notif_mod.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(response)
    )


def _notif(channel=NotificationChannel.SLACK, **kw):
    return Notification(title="T", message="M", channel=channel, **kw)


async def test_email_console_fallback(monkeypatch):
    notifier = EmailNotifier()
    monkeypatch.setattr(notifier, "provider", "console")
    result = await notifier.send(_notif(channel=NotificationChannel.EMAIL, recipient="a@b.c"))
    assert result == {"success": True, "provider": "console"}


async def test_slack_console_fallback_without_token():
    notifier = SlackNotifier()
    notifier.bot_token = None
    result = await notifier.send(_notif(recipient="#chan"))
    assert result["success"] is True
    assert result["provider"] == "console"


async def test_slack_send_with_token(monkeypatch):
    _patch_client(monkeypatch, FakeResponse(payload={"ok": True, "ts": "1.23"}))
    notifier = SlackNotifier()
    notifier.bot_token = "xoxb-test"
    result = await notifier.send(_notif(recipient="#chan"))
    assert result == {
        "success": True,
        "message_ts": "1.23",
        "error": None,
        "provider": "slack",
    }
    assert FakeAsyncClient.last_call["url"].endswith("/chat.postMessage")


async def test_slack_blocks_include_action_button():
    notifier = SlackNotifier()
    blocks = notifier._format_blocks(
        _notif(
            priority=NotificationPriority.CRITICAL,
            action_url="https://x.io/s",
            action_text="Open",
            metadata={"k": "v"},
        )
    )
    types = [b["type"] for b in blocks]
    assert types[0] == "header"
    assert "actions" in types
    assert ":rotating_light:" in blocks[0]["text"]["text"]


async def test_webhook_success(monkeypatch):
    _patch_client(monkeypatch, FakeResponse(status_code=204))
    result = await WebhookNotifier().send(
        _notif(channel=NotificationChannel.WEBHOOK), "https://hook.test/x"
    )
    assert result == {"success": True, "status_code": 204, "provider": "webhook"}
    assert FakeAsyncClient.last_call["url"] == "https://hook.test/x"


async def test_webhook_handles_exception(monkeypatch):
    class BoomClient(FakeAsyncClient):
        async def post(self, url, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(
        notif_mod.httpx, "AsyncClient", lambda *a, **k: BoomClient(FakeResponse())
    )
    result = await WebhookNotifier().send(
        _notif(channel=NotificationChannel.WEBHOOK), "https://hook.test/x"
    )
    assert result["success"] is False
    assert result["provider"] == "webhook"


async def test_manager_routes_and_rejects_unknown(monkeypatch):
    mgr = NotificationManager()
    monkeypatch.setattr(mgr.slack, "bot_token", None)
    slack_result = await mgr.send(_notif(channel=NotificationChannel.SLACK))
    assert slack_result["provider"] == "console"

    with pytest.raises(ValueError):
        await mgr.send(_notif(channel=NotificationChannel.WEBHOOK))  # no webhook_url


async def test_notify_score_change_includes_email_recipients(monkeypatch):
    mgr = NotificationManager()
    monkeypatch.setattr(mgr.slack, "bot_token", None)
    monkeypatch.setattr(mgr.email, "provider", "console")

    results = await mgr.notify_startup_score_change(
        startup_id=uuid4(),
        startup_name="Acme",
        bot_name="runway",
        old_score=40.0,
        new_score=70.0,
        threshold_crossed="alert",
        recipients=["a@b.c", "d@e.f"],
    )
    # 1 slack + 2 email.
    assert len(results) == 3
    assert all(r["success"] for r in results)
