"""Tests for the Slack integration (slack-bolt is a lazy/optional dependency)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from startupintel.db.models import Startup, StartupScore
from startupintel.slack.bot import SlackBot, get_slack_bot, set_slack_bot
from startupintel.slack.commands import SlackCommands
from startupintel.slack.digest import SlackDigest, post_daily_summary

pytestmark = pytest.mark.asyncio


class FakeSayRecorder:
    def __init__(self) -> None:
        self.messages: list = []

    async def __call__(self, message) -> None:
        self.messages.append(message)


class FakeSlackClient:
    def __init__(self) -> None:
        self.posted: list[dict] = []

    async def chat_postMessage(self, **kwargs) -> None:
        self.posted.append(kwargs)


class FakeApp:
    """Stand-in for slack_bolt AsyncApp, capturing decorator registrations."""

    def __init__(self) -> None:
        self.client = FakeSlackClient()
        self.commands: dict[str, object] = {}
        self.events: dict[str, object] = {}

    def command(self, name):
        def deco(fn):
            self.commands[name] = fn
            return fn

        return deco

    def event(self, name):
        def deco(fn):
            self.events[name] = fn
            return fn

        return deco


async def test_start_raises_without_slack_bolt():
    bot = SlackBot(bot_token="xoxb-test")
    with pytest.raises(ImportError):
        await bot.start()


async def test_send_alert_noop_when_not_started():
    bot = SlackBot(bot_token="xoxb-test")
    # Should warn and return without raising (no app yet).
    await bot.send_alert("#chan", "hello")


async def test_send_alert_posts_via_client():
    bot = SlackBot(bot_token="xoxb-test")
    bot._app = FakeApp()
    await bot.send_alert("#chan", "hello", blocks=[{"type": "section"}])
    posted = bot._app.client.posted[0]
    assert posted["channel"] == "#chan"
    assert posted["text"] == "hello"


async def test_stress_and_pmf_alerts_build_blocks():
    bot = SlackBot(bot_token="xoxb-test")
    bot._app = FakeApp()
    await bot.send_high_stress_alert("#chan", "Acme", 78.0)
    await bot.send_pmf_inflection_alert("#chan", "Acme", 75.0)
    headers = [p["blocks"][0]["text"]["text"] for p in bot._app.client.posted]
    assert any("High Stress Alert: Acme" in h for h in headers)
    assert any("PMF Inflection: Acme" in h for h in headers)


async def test_global_bot_accessors():
    assert get_slack_bot() is None or isinstance(get_slack_bot(), SlackBot)
    bot = SlackBot(bot_token="xoxb-test")
    set_slack_bot(bot)
    assert get_slack_bot() is bot
    set_slack_bot(None)  # reset for other tests


async def test_commands_register_and_help():
    app = FakeApp()
    SlackCommands(app)
    assert "/startupintel" in app.commands
    assert "/stress" in app.commands
    assert "/termsheet" in app.commands

    say = FakeSayRecorder()
    cmds = SlackCommands(app)
    await cmds._handle_help({}, say)
    await cmds._handle_status({}, say)
    assert any("Commands" in m for m in say.messages)
    assert any("System Status" in m for m in say.messages)


async def test_stress_command_requires_argument():
    app = FakeApp()
    SlackCommands(app)
    say = FakeSayRecorder()
    await app.commands["/stress"](ack=_noop_ack, command={"text": ""}, say=say)
    assert "Usage" in say.messages[0]


async def _noop_ack() -> None:
    return None


async def test_digest_returns_false_without_bot():
    set_slack_bot(None)
    assert await SlackDigest().generate_and_post() is False
    assert await post_daily_summary() is False


async def test_digest_posts_high_scores(db_session):
    startup = Startup(name="Acme", domain=f"{uuid4().hex[:8]}.io", industry="saas")
    db_session.add(startup)
    await db_session.flush()
    db_session.add(
        StartupScore(startup_id=startup.id, bot_name="runway", score=78.0)
    )
    await db_session.commit()

    bot = SlackBot(bot_token="xoxb-test")
    bot._app = FakeApp()
    set_slack_bot(bot)
    try:
        assert await SlackDigest(channel="#chan").generate_and_post() is True
        posted = bot._app.client.posted[0]
        assert "Acme" in posted["text"]
        assert "Digest" in posted["text"]
    finally:
        set_slack_bot(None)
