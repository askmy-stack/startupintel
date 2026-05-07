from uuid import UUID

from startupintel.bots.base import BaseBot, BotResult
from startupintel.config import get_settings
from startupintel.events.topics import STARTUP_STRESS_HIGH


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
        raise NotImplementedError("RunwayBot fetch_signals requires connector wiring.")

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

