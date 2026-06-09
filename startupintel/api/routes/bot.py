"""Bot management and status API routes."""


from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from startupintel.api.dependencies import DbDep
from startupintel.api.schemas import BotRunResponse, BotScoreListResponse
from startupintel.db.models import StartupScore

router = APIRouter(prefix="/bot", tags=["bots"])


@router.get("/status")
async def get_bot_status() -> dict:
    """Get overall bot system status."""
    return {
        "bots": {
            "runway": {"status": "active", "description": "Financial stress detection"},
            "obituary": {"status": "active", "description": "Failure pattern matching"},
            "term": {"status": "active", "description": "Term sheet analysis"},
            "pivot": {"status": "active", "description": "Pivot detection"},
            "pmf": {"status": "active", "description": "Product-market fit analysis"},
            "accelerator": {"status": "active", "description": "Accelerator ROI ranking"},
            "investor": {"status": "active", "description": "Investor network analysis"},
            "acqui": {"status": "active", "description": "Acqui-hire prediction"},
        },
        "total_bots": 8,
        "active_bots": 8,
    }


@router.get("/{bot_name}/results", response_model=BotScoreListResponse)
async def get_bot_results(
    bot_name: str,
    db: DbDep,
    limit: int = 20,
) -> BotScoreListResponse:
    """Get all results for a specific bot."""
    # Validate bot name
    valid_bots = ["runway", "obituary", "term", "pivot", "pmf", "accelerator", "investor", "acqui"]
    if bot_name not in valid_bots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot name. Valid options: {valid_bots}",
        )

    result = await db.execute(
        select(StartupScore)
        .where(StartupScore.bot_name == bot_name)
        .order_by(StartupScore.computed_at.desc())
        .limit(limit)
    )
    scores = result.scalars().all()

    return BotScoreListResponse(
        items=[BotRunResponse(
            startup_id=s.startup_id,
            bot_name=s.bot_name,
            score=s.score,
            status="completed",
            computed_at=s.computed_at,
        ) for s in scores],
        total=len(scores),
    )


@router.get("/{bot_name}/stats")
async def get_bot_stats(
    bot_name: str,
    db: DbDep,
) -> dict:
    """Get statistics for a specific bot."""
    valid_bots = ["runway", "obituary", "term", "pivot", "pmf", "accelerator", "investor", "acqui"]
    if bot_name not in valid_bots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot name. Valid options: {valid_bots}",
        )

    # Get aggregate stats
    result = await db.execute(
        select(
            func.count().label("total"),
            func.avg(StartupScore.score).label("avg_score"),
            func.min(StartupScore.score).label("min_score"),
            func.max(StartupScore.score).label("max_score"),
        )
        .where(StartupScore.bot_name == bot_name)
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
async def get_recent_scores(
    db: DbDep,
    limit: int = 50,
) -> list[dict]:
    """Get recent bot scores across all bots."""
    result = await db.execute(
        select(StartupScore)
        .order_by(StartupScore.computed_at.desc())
        .limit(limit)
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
