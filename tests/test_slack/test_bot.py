"""Tests for Slack bot."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from startupintel.slack.bot import SlackBot, get_slack_bot, set_slack_bot


@pytest.fixture
def slack_bot():
    """Create Slack bot for testing."""
    return SlackBot(bot_token="xoxb-test-token", app_token="xapp-test-token")


def test_slack_bot_init(slack_bot):
    """Test Slack bot initialization."""
    assert slack_bot.bot_token == "xoxb-test-token"
    assert slack_bot.app_token == "xapp-test-token"
    assert slack_bot._app is None


@pytest.mark.asyncio
async def test_slack_bot_start(slack_bot):
    """Test Slack bot start."""
    with patch("slack_bolt.async_app.AsyncApp") as mock_app_class:
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        await slack_bot.start()
        assert slack_bot._app is mock_app


@pytest.mark.asyncio
async def test_slack_bot_singleton():
    """Test Slack bot singleton pattern."""
    # Clear existing bot
    set_slack_bot(None)

    # Get should return None initially
    assert get_slack_bot() is None

    # Set a bot
    bot = SlackBot(bot_token="test")
    set_slack_bot(bot)

    # Get should return the set bot
    assert get_slack_bot() is bot


@pytest.mark.asyncio
async def test_send_alert_without_bot(slack_bot):
    """Test sending alert when bot not started."""
    # Should not raise error, just log warning
    await slack_bot.send_alert("#test", "Test message")


@pytest.mark.asyncio
async def test_send_high_stress_alert(slack_bot):
    """Test sending high stress alert."""
    with patch.object(slack_bot, "send_alert") as mock_send:
        mock_send.return_value = None

        await slack_bot.send_high_stress_alert("#alerts", "Acme Inc", 78.5)

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "#alerts"
        assert "Acme Inc" in call_args[0][1]
        assert call_args[1]["blocks"] is not None


@pytest.mark.asyncio
async def test_send_pmf_inflection_alert(slack_bot):
    """Test sending PMF inflection alert."""
    with patch.object(slack_bot, "send_alert") as mock_send:
        mock_send.return_value = None

        await slack_bot.send_pmf_inflection_alert("#alerts", "Quantum Health", 75.0)

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Quantum Health" in call_args[0][1]
        assert "PMF Inflection" in call_args[0][1]
