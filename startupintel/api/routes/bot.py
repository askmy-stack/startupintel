"""Bot status and score-reporting routes (read-only over StartupScore)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from startupintel.api.dependencies import DbDep
from startupintel.api.schemas import BotRunResponse, BotScoreListResponse
from startupintel.db.models import StartupScore

router = APIRouter(prefix="/bot", tags=["bots"])

_VALID_BOTS = [
    "runway",
    "obituary",
    "term",
    "pivot",
    "pmf",
    "accelerator",
    "investor",
    "acqui",
]

_BOT_DESCRIPTIONS = {
    "runway": "Financial stress detection",
    "obituary": "Failure pattern matching",
    "term": "Term sheet analysis",
    "pivot": "Pivot detection",
    "pmf": "Product-market fit analysis",
    "accelerator": "Accelerator ROI ranking",
    "investor": "Investor network analysis",
    "acqui": "Acqui-hire prediction",
}


def _ensure_valid_bot(bot_name: str) -> None:
    if bot_name not in _VALID_BOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot name. Valid options: {_VALID_BOTS}",
        )


@router.get("/status")
async def get_bot_status() -> dict:
    """Report the registered bots and their static status."""
    return {
        "bots": {
            name: {"status": "active", "description": desc}
            for name, desc in _BOT_DESCRIPTIONS.items()
        },
        "total_bots": len(_VALID_BOTS),
        "active_bots": len(_VALID_BOTS),
    }


@router.get("/{bot_name}/results", response_model=BotScoreListResponse)
async def get_bot_results(
    bot_name: str,
    db: DbDep,
    limit: int = 20,
) -> BotScoreListResponse:
    """Return the most recent scores produced by a single bot."""
    _ensure_valid_bot(bot_name)

    result = await db.execute(
        select(StartupScore)
        .where(StartupScore.bot_name == bot_name)
        .order_by(StartupScore.computed_at.desc())
        .limit(limit)
    )
    scores = result.scalars().all()

    return BotScoreListResponse(
        items=[
            BotRunResponse(
                startup_id=s.startup_id,
                bot_name=s.bot_name,
                score=s.score,
                status="completed",
                computed_at=s.computed_at,
            )
            for s in scores
        ],
        total=len(scores),
    )


@router.get("/{bot_name}/stats")
async def get_bot_stats(bot_name: str, db: DbDep) -> dict:
    """Return aggregate score statistics for a single bot."""
    _ensure_valid_bot(bot_name)

    result = await db.execute(
        select(
            func.count().label("total"),
            func.avg(StartupScore.score).label("avg_score"),
            func.min(StartupScore.score).label("min_score"),
            func.max(StartupScore.score).label("max_score"),
        ).where(StartupScore.bot_name == bot_name)
    )
    stats = result.one()

    return {
        "bot_name": bot_name,
        "total_analyses": stats.total or 0,
        "average_score": round(stats.avg_score, 2) if stats.avg_score else 0,
        "min_score": round(stats.min_score, 2) if stats.min_score else 0,
        "max_score": round(stats.max_score, 2) if stats.max_score else 0,
    }


@router.get("/scores/recent")
async def get_recent_scores(db: DbDep, limit: int = 50) -> list[dict]:
    """Return the most recent scores across all bots."""
    result = await db.execute(
        select(StartupScore).order_by(StartupScore.computed_at.desc()).limit(limit)
    )
    scores = result.scalars().all()

    return [
        {
            "id": s.id,
            "startup_id": s.startup_id,
            "bot_name": s.bot_name,
            "score": s.score,
            "computed_at": s.computed_at,
        }
        for s in scores
    ]
