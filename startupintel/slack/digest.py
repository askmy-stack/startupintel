"""Slack digest generation and posting."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from startupintel.slack.bot import get_slack_bot

logger = logging.getLogger(__name__)


class SlackDigest:
    """Generate and post weekly digest to Slack."""

    def __init__(self, channel: str = "#startupintel"):
        self.channel = channel

    async def generate_and_post(self) -> bool:
        """Generate digest and post to Slack."""
        bot = get_slack_bot()
        if not bot:
            logger.warning("Slack bot not available, digest not posted")
            return False

        try:
            # Import here to avoid circular imports
            from startupintel.db.postgres import AsyncSessionLocal
            from startupintel.db.models import StartupScore, Startup
            from sqlalchemy import select, desc

            db = AsyncSessionLocal()
            try:
                # Get recent high scores
                one_week_ago = datetime.utcnow() - timedelta(days=7)

                result = await db.execute(
                    select(StartupScore, Startup.name)
                    .join(Startup, StartupScore.startup_id == Startup.id)
                    .where(StartupScore.computed_at >= one_week_ago)
                    .where(StartupScore.score >= 60)  # High scores only
                    .order_by(desc(StartupScore.score))
                    .limit(10)
                )

                scores = result.all()

                if not scores:
                    await bot.send_alert(
                        self.channel,
                        "📊 *Weekly Digest*\n\nNo significant alerts this week. All monitored startups are within normal parameters."
                    )
                    return True

                # Build digest message
                sections = []

                # Group by bot type
                by_bot = {}
                for score, startup_name in scores:
                    bot_name = score.bot_name
                    if bot_name not in by_bot:
                        by_bot[bot_name] = []
                    by_bot[bot_name].append({
                        "name": startup_name,
                        "score": score.score,
                    })

                # Format sections
                bot_emoji = {
                    "runway": "🏃",
                    "obituary": "⚰️",
                    "pmf": "🎯",
                    "pivot": "🔄",
                    "acqui": "💰",
                    "investor": "💼",
                    "accelerator": "🚀",
                    "term": "📄",
                }

                for bot_name, items in by_bot.items():
                    emoji = bot_emoji.get(bot_name, "📊")
                    section_lines = [f"*{emoji} {bot_name.title()}Bot Alerts*"]

                    for item in items[:5]:  # Top 5 per bot
                        section_lines.append(f"• {item['name']}: {item['score']:.0f}/100")

                    sections.append("\n".join(section_lines))

                week_of = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
                sections_text = "\n\n".join(sections)
                message = f"""📊 *Weekly StartupIntel Digest*
*Week of {week_of}*

{sections_text}

_Use `/analyze <startup>` for detailed insights._
"""

                await bot.send_alert(self.channel, message)
                return True

            finally:
                await db.close()

        except Exception as e:
            logger.error(f"Failed to generate Slack digest: {e}")
            return False


async def post_daily_summary() -> bool:
    """Post daily summary to Slack."""
    digest = SlackDigest()
    return await digest.generate_and_post()
