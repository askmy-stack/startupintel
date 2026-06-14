"""Slack bot for StartupIntel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slack_bolt.async_app import AsyncApp

logger = logging.getLogger(__name__)


class SlackBot:
    """Slack bot integration for StartupIntel."""

    def __init__(self, bot_token: str, app_token: str | None = None):
        self.bot_token = bot_token
        self.app_token = app_token
        self._app: AsyncApp | None = None

    async def start(self) -> None:
        """Initialize and start the Slack bot."""
        try:
            from slack_bolt.async_app import AsyncApp

            self._app = AsyncApp(token=self.bot_token)

            # Register event handlers
            self._register_handlers()

            logger.info("Slack bot initialized")
        except ImportError:
            logger.error("slack-bolt not installed. Install with: pip install slack-bolt")
            raise

    def _register_handlers(self) -> None:
        """Register Slack event handlers."""
        if not self._app:
            return

        @self._app.event("app_mention")
        async def handle_mention(body, say, client):
            """Handle when bot is mentioned."""
            text = body.get("event", {}).get("text", "")
            user = body.get("event", {}).get("user", "")

            # Simple command parsing
            if "health" in text.lower():
                await say(":white_check_mark: StartupIntel bot is operational!")
            elif "help" in text.lower():
                await self._show_help(say)
            elif "analyze" in text.lower():
                await say("Use `/analyze <startup_name>` to analyze a startup.")
            else:
                await say(f"Hi <@{user}>! Type `help` to see what I can do.")

        @self._app.command("/analyze")
        async def handle_analyze_command(ack, command, say):
            """Handle /analyze command."""
            await ack()
            startup_name = command.get("text", "").strip()

            if not startup_name:
                await say("Please provide a startup name. Usage: `/analyze <startup_name>`")
                return

            await say(f"🔍 Analyzing *{startup_name}*...")

            # Trigger analysis (placeholder)
            try:
                result = await self._analyze_startup(startup_name)
                await say(result)
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                await say(f"❌ Analysis failed: {e}")

        @self._app.command("/runway")
        async def handle_runway_command(ack, command, say):
            """Handle /runway command for stress check."""
            await ack()
            startup_name = command.get("text", "").strip()

            if not startup_name:
                await say("Usage: `/runway <startup_name>`")
                return

            await say(f"🏃 Checking runway for *{startup_name}*...")
            # Placeholder for actual bot run
            await say(f"📊 *{startup_name}* runway score: 65/100 (moderate stress)")

        @self._app.command("/pmf")
        async def handle_pmf_command(ack, command, say):
            """Handle /pmf command for PMF check."""
            await ack()
            startup_name = command.get("text", "").strip()

            if not startup_name:
                await say("Usage: `/pmf <startup_name>`")
                return

            await say(f"🎯 Checking PMF for *{startup_name}*...")
            # Placeholder
            await say(f"📈 *{startup_name}* PMF score: 72/100 (product-market fit developing)")

        @self._app.command("/digest")
        async def handle_digest_command(ack, command, say):
            """Handle /digest command for weekly digest."""
            await ack()
            await say("📋 Generating weekly digest...")
            # Placeholder - would integrate with digest generation
            await say("""📊 *Weekly StartupIntel Digest*

*Top Alerts:*
• Acme Analytics: Runway stress elevated (score: 78)
• Quantum Health: PMF inflection detected
• GreenLeaf AI: Positive sentiment trend

Use `/analyze <name>` for detailed analysis.""")

    async def _show_help(self, say) -> None:
        """Show help message."""
        help_text = """
*StartupIntel Bot Commands:*

• `/analyze <startup_name>` - Full startup analysis
• `/runway <startup_name>` - Check financial runway stress
• `/pmf <startup_name>` - Check product-market fit
• `/digest` - Get weekly digest
• `help` - Show this message

*I can also:*
• Alert you to high-stress signals
• Notify on PMF inflections
• Summarize term sheet analyses
        """
        await say(help_text)

    async def _analyze_startup(self, name: str) -> str:
        """Analyze a startup and return formatted result."""
        # This would integrate with the actual API/bots
        return f"""
📊 *Analysis for {name}*

🏃 *Runway:* 65/100 (moderate stress)
🎯 *PMF:* 72/100 (developing)
⚰️ *Obituary:* 45/100 (low risk)
🔄 *Pivot:* 38/100 (stable)
💰 *Acqui:* 55/100 (medium probability)

*Recommendation:* Monitor closely, positive PMF trajectory.
        """

    async def send_alert(self, channel: str, message: str, blocks: list | None = None) -> None:
        """Send an alert to a Slack channel."""
        if not self._app:
            logger.warning("Slack bot not started, alert not sent")
            return

        try:
            await self._app.client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=blocks,
            )
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    async def send_high_stress_alert(self, channel: str, startup_name: str, score: float) -> None:
        """Send high stress alert."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ High Stress Alert: {startup_name}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Runway Score:* {score:.1f}/100\n*Status:* Financial stress detected",
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Analysis",
                        },
                        "action_id": "view_analysis",
                    }
                ]
            }
        ]
        await self.send_alert(channel, f"High stress alert for {startup_name}", blocks)

    async def send_pmf_inflection_alert(self, channel: str, startup_name: str, score: float) -> None:
        """Send PMF inflection alert."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 PMF Inflection: {startup_name}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*PMF Score:* {score:.1f}/100\n*Status:* Product-market fit detected!",
                }
            }
        ]
        await self.send_alert(channel, f"PMF inflection for {startup_name}", blocks)


# Global bot instance
_slack_bot: SlackBot | None = None


def get_slack_bot() -> SlackBot | None:
    """Get the global Slack bot instance."""
    return _slack_bot


def set_slack_bot(bot: SlackBot) -> None:
    """Set the global Slack bot instance."""
    global _slack_bot
    _slack_bot = bot
