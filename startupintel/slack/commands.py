"""Slack slash command handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slack_bolt.async_app import AsyncApp

logger = logging.getLogger(__name__)


class SlackCommands:
    """Slack slash command handlers."""

    def __init__(self, app: AsyncApp):
        self.app = app
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all slash commands."""

        @self.app.command("/startupintel")
        async def handle_startupintel(ack, command, say):
            """Main StartupIntel command."""
            await ack()

            subcommand = command.get("text", "").strip().split()[0] if command.get("text") else "help"

            handlers = {
                "help": self._handle_help,
                "search": self._handle_search,
                "status": self._handle_status,
                "alerts": self._handle_alerts,
            }

            handler = handlers.get(subcommand, self._handle_help)
            await handler(command, say)

        @self.app.command("/stress")
        async def handle_stress(ack, command, say):
            """Quick stress check command."""
            await ack()
            startup = command.get("text", "").strip()

            if not startup:
                await say("Usage: `/stress <startup_name>`")
                return

            await say(f"🏃 Checking stress signals for *{startup}*...")
            # Would call actual API here
            await say(f"⚠️ *{startup}* stress level: Elevated (score: 72/100)")

        @self.app.command("/acqui")
        async def handle_acqui(ack, command, say):
            """Acqui-hire prediction command."""
            await ack()
            startup = command.get("text", "").strip()

            if not startup:
                await say("Usage: `/acqui <startup_name>`")
                return

            await say(f"💰 Predicting acqui-hire probability for *{startup}*...")
            await say(f"📊 *{startup}* acqui probability: 58% (likely acquirers: Google, Microsoft)")

        @self.app.command("/termsheet")
        async def handle_termsheet(ack, command, say):
            """Term sheet analysis command."""
            await ack()

            text = command.get("text", "").strip()
            if not text:
                await say("Usage: `/termsheet <startup_name>` or upload a file")
                return

            await say(f"📄 Analyzing term sheet for *{text}*...")
            await say("""📊 *Term Sheet Analysis*

*Founder Friendliness:* 68/100

*Red Flags:*
• No-shop clause: 60 days (recommended: 30 days)
• Board composition: 2:1 investor favor

*Positive:*
• 1x non-participating liquidation preference
• Standard 4-year vesting with cliff
""")

    async def _handle_help(self, command: dict, say) -> None:
        """Handle help subcommand."""
        help_text = """*StartupIntel Commands:*

• `/startupintel search <query>` - Search startups
• `/startupintel status` - System status
• `/startupintel alerts` - Recent alerts
• `/analyze <startup>` - Full analysis
• `/stress <startup>` - Quick stress check
• `/pmf <startup>` - PMF check
• `/acqui <startup>` - Acqui prediction
• `/termsheet <startup>` - Term sheet analysis
• `/digest` - Weekly digest
• `/startupintel help` - Show this message
"""
        await say(help_text)

    async def _handle_search(self, command: dict, say) -> None:
        """Handle search subcommand."""
        query = command.get("text", "").replace("search", "").strip()

        if not query:
            await say("Usage: `/startupintel search <query>`")
            return

        await say(f"🔍 Searching for *{query}*...")
        # Would call actual API
        await say("""*Search Results:*
• Acme Analytics (SaaS, Seed, $4.2M raised)
• Acme Corp (Fintech, Series A, $12M raised)
• Acme Labs (AI, Pre-seed, $500K raised)""")

    async def _handle_status(self, command: dict, say) -> None:
        """Handle status subcommand."""
        await say("""*StartupIntel System Status:*

🟢 *API:* Operational
🟢 *Database:* Connected
🟢 *LLM:* Groq (llama-3.3-70b)
🟢 *RAG Index:* Loaded (1,234 documents)
⚪ *Kafka:* Standby (in-memory mode)

*Last updated:* Just now""")

    async def _handle_alerts(self, command: dict, say) -> None:
        """Handle alerts subcommand."""
        await say("""*Recent Alerts (24h):*

⚠️ *High Stress:*
• Acme Analytics: 78/100
• CryptoVault: 82/100

🎯 *PMF Inflection:*
• Quantum Health: 75/100

⚰️ *Obituary Match:*
• None

🔄 *Pivot Detected:*
• GreenLeaf AI: 68/100 confidence""")
