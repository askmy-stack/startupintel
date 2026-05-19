"""RunwayBot - Financial stress detection from headcount, hiring, sentiment, domain, funding."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from startupintel.bots.base import BaseBot, BotResult
from startupintel.config import get_settings
from startupintel.db.models import HeadcountSnapshot, Startup
from startupintel.events.topics import STARTUP_STRESS_HIGH
from startupintel.ingestion.domain_whois import DomainWHOISConnector
from startupintel.ingestion.job_boards import JobBoardsConnector
from startupintel.ingestion.linkedin import LinkedInConnector
from startupintel.ingestion.twitter import TwitterConnector


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class RunwayBot(BaseBot):
    name = "runway"
    required_signals = [
        "headcount_delta_pct",
        "job_posting_delta_pct",
        "founder_sentiment",
        "domain_expiry_days",
        "days_since_funding",
    ]

    async def fetch_signals(self, startup_id: UUID) -> dict:
        """Fetch runway signals from database and external sources."""
        signals = {"startup_id": str(startup_id)}

        # Get startup info from database
        if self.db:
            startup = await self.db.get(Startup, startup_id)
            if startup:
                signals.update({
                    "company_name": startup.name,
                    "domain": startup.domain,
                    "last_funding_date": startup.last_funding_date,
                    "employee_count": startup.employee_count,
                })

                # Calculate days since funding
                if startup.last_funding_date:
                    days_since = (datetime.utcnow() - startup.last_funding_date.replace(tzinfo=None)).days
                    signals["days_since_funding"] = days_since
                else:
                    signals["days_since_funding"] = 365  # Default assumption

        # Get headcount history and calculate delta
        signals["headcount_delta_pct"] = await self._get_headcount_delta(startup_id)

        # Get job posting signals
        signals["job_posting_delta_pct"] = await self._get_job_posting_delta(signals.get("company_name"))

        # Get founder sentiment
        signals["founder_sentiment"] = await self._get_founder_sentiment(signals.get("company_name"))

        # Get domain expiry
        signals["domain_expiry_days"] = await self._get_domain_expiry(signals.get("domain"))

        return signals

    async def _get_headcount_delta(self, startup_id: UUID) -> float:
        """Calculate headcount change percentage over last 30 days."""
        if not self.db:
            return 0.0

        from sqlalchemy import select
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=30)

        result = await self.db.execute(
            select(HeadcountSnapshot)
            .where(HeadcountSnapshot.startup_id == startup_id)
            .where(HeadcountSnapshot.snapshot_date >= cutoff)
            .order_by(HeadcountSnapshot.snapshot_date)
        )
        snapshots = result.scalars().all()

        if len(snapshots) < 2:
            return 0.0

        oldest = snapshots[0].headcount
        newest = snapshots[-1].headcount

        if oldest == 0:
            return 0.0

        return (newest - oldest) / oldest

    async def _get_job_posting_delta(self, company_name: str | None) -> float:
        """Get job posting change from job boards."""
        if not company_name:
            return 0.0

        try:
            connector = JobBoardsConnector()
            data = await connector.fetch(company_name)

            if data.get("found"):
                total = data.get("total_postings", 0)
                # Normalize: 0 jobs = -1 (bad), 10+ jobs = 1 (good)
                if total == 0:
                    return -1.0
                return min(1.0, total / 10.0)

        except Exception:
            pass

        return 0.0

    async def _get_founder_sentiment(self, company_name: str | None) -> float:
        """Get founder sentiment from Twitter."""
        if not company_name:
            return 0.0

        # Try to find founder Twitter handle (simplified)
        # In real implementation, this would be looked up from database
        settings = get_settings()
        if not settings.twitter_bearer_token:
            return 0.0

        try:
            # Search for company mentions
            connector = TwitterConnector()
            mentions = await connector.search_mentions(f"{company_name} startup", days=7)

            # Calculate sentiment from mentions
            texts = [m.get("text", "") for m in mentions.get("results", [])]

            if not texts:
                return 0.0

            from textblob import TextBlob
            sentiments = [TextBlob(t).sentiment.polarity for t in texts]
            avg_sentiment = sum(sentiments) / len(sentiments)

            return avg_sentiment

        except Exception:
            return 0.0

    async def _get_domain_expiry(self, domain: str | None) -> float:
        """Get days until domain expiry."""
        if not domain:
            return 90.0  # Default assumption

        try:
            connector = DomainWHOISConnector()
            data = await connector.fetch(domain)

            if data.get("found"):
                days = data.get("days_until_expiry")
                if days is not None:
                    return float(days)

        except Exception:
            pass

        return 90.0  # Default assumption

    async def compute_score(self, raw: dict) -> dict[str, float]:
        headcount_delta = float(raw.get("headcount_delta_pct", 0.0))
        job_delta = float(raw.get("job_posting_delta_pct", 0.0))
        sentiment = float(raw.get("founder_sentiment", 0.0))
        domain_days = float(raw.get("domain_expiry_days", 90.0))
        funding_days = float(raw.get("days_since_funding", 365.0))

        return {
            "headcount": clamp((-headcount_delta + 0.3) / 0.6),
            "job_postings": clamp((-job_delta + 0.5) / 1.0),
            "sentiment": clamp((-sentiment + 1.0) / 2.0),
            "domain_renewal": clamp((90.0 - domain_days) / 90.0),
            "funding_recency": clamp((funding_days - 365.0) / 365.0),
        }

    def get_weights(self) -> dict[str, float]:
        settings = get_settings()
        return {
            "headcount": settings.runway_weight_headcount,
            "job_postings": settings.runway_weight_job_postings,
            "sentiment": settings.runway_weight_sentiment,
            "domain_renewal": settings.runway_weight_domain,
            "funding_recency": settings.runway_weight_funding_recency,
        }

    def risk_level(self, score: float) -> str:
        if score <= 25:
            return "low"
        if score <= 50:
            return "monitor"
        if score <= 75:
            return "elevated"
        return "high"

    def build_rag_query(self, raw: dict) -> str:
        return (
            f"runway stress headcount {raw.get('headcount_delta_pct')} "
            f"jobs {raw.get('job_posting_delta_pct')} funding {raw.get('days_since_funding')}"
        )

    def diagnosis_prompt_template(self) -> str:
        return (
            "You are a startup analyst detecting financial distress signals.\n"
            "Startup runway stress score: {score}/100\n"
            "Headcount change (30d): {headcount_delta}%\n"
            "Job postings change (30d): {job_posting_delta}%\n"
            "Founder sentiment (7d avg): {sentiment}\n"
            "Domain expires in: {domain_expiry_days} days\n"
            "Days since last funding: {days_since_funding}\n"
            "Most similar historical cases: {similar_cases}\n\n"
            "Write 3 sentences with concrete numbers and no filler."
        )

    async def maybe_emit_event(self, result: BotResult) -> None:
        threshold = get_settings().runway_high_stress_threshold
        if result.score <= threshold or self.producer is None:
            return
        await self.producer.emit(
            STARTUP_STRESS_HIGH,
            {
                "startup_id": str(result.startup_id),
                "score": result.score,
                "bot_name": result.bot_name,
                "computed_at": result.computed_at.isoformat(),
            },
        )

