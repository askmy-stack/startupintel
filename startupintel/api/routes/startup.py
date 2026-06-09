from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from startupintel.api.dependencies import DbDep, get_startup_or_404
from startupintel.api.schemas import (
    RunwayBotOutput,
    StartupCreate,
    StartupListResponse,
    StartupResponse,
)
from startupintel.bots.runway_bot import RunwayBot
from startupintel.db.models import Startup

router = APIRouter(prefix="/startup", tags=["startup"])


@router.post("", response_model=StartupResponse, status_code=status.HTTP_201_CREATED)
async def create_startup(db: DbDep, data: StartupCreate) -> Startup:
    startup = Startup(**data.model_dump())
    db.add(startup)
    await db.commit()
    await db.refresh(startup)
    return startup


@router.get("", response_model=StartupListResponse)
async def list_startups(
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StartupListResponse:
    total = await db.scalar(select(func.count()).select_from(Startup))
    result = await db.execute(
        select(Startup)
        .order_by(Startup.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return StartupListResponse(items=list(result.scalars().all()), total=total or 0)


@router.get("/{startup_id}", response_model=StartupResponse)
async def get_startup(startup_id: UUID, db: DbDep) -> Startup:
    return await get_startup_or_404(db, startup_id)


@router.delete("/{startup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_startup(startup_id: UUID, db: DbDep) -> None:
    startup = await get_startup_or_404(db, startup_id)
    await db.delete(startup)
    await db.commit()


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

