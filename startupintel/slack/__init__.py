"""Slack integration for StartupIntel."""

from startupintel.slack.bot import SlackBot, get_slack_bot, set_slack_bot
from startupintel.slack.digest import SlackDigest, post_daily_summary
from startupintel.slack.commands import SlackCommands

__all__ = [
    "SlackBot",
    "get_slack_bot",
    "set_slack_bot",
    "SlackDigest",
    "post_daily_summary",
    "SlackCommands",
]
