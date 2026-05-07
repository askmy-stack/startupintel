from uuid import UUID

from fastapi import APIRouter, HTTPException

from startupintel.api.schemas import RunwayBotOutput
from startupintel.bots.runway_bot import RunwayBot

router = APIRouter(prefix="/startup", tags=["startup"])


DEMO_SIGNALS = {
    "headcount_delta_pct": -0.18,
    "job_posting_delta_pct": -0.72,
    "founder_sentiment": -0.35,
    "domain_expiry_days": 21,
    "days_since_funding": 640,
}


class DemoRunwayBot(RunwayBot):
    async def fetch_signals(self, startup_id: UUID) -> dict:
        return DEMO_SIGNALS | {"startup_id": str(startup_id)}


@router.get("/{startup_id}/stress", response_model=RunwayBotOutput)
async def startup_stress(startup_id: UUID) -> RunwayBotOutput:
    bot = DemoRunwayBot()
    result = await bot.run(startup_id)
    raw = result.raw_signals
    if not raw:
        raise HTTPException(status_code=404, detail="No runway signals found")
    return RunwayBotOutput(
        startup_id=startup_id,
        score=result.score,
        risk_level=bot.risk_level(result.score),
        signal_breakdown=result.signal_breakdown,
        headcount_delta_pct=raw["headcount_delta_pct"],
        job_posting_delta_pct=raw["job_posting_delta_pct"],
        founder_sentiment=raw["founder_sentiment"],
        domain_expiry_days=raw["domain_expiry_days"],
        days_since_funding=raw["days_since_funding"],
        similar_cases=result.similar_cases,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )

