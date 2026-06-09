"""Accelerator API routes."""

from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func

from startupintel.api.dependencies import DbDep, get_accelerator_or_404
from startupintel.api.schemas import (
    AcceleratorCreate,
    AcceleratorResponse,
    AcceleratorListResponse,
    AcceleratorBotOutput,
)
from startupintel.bots.accelerator_bot import AcceleratorBot
from startupintel.db.models import Accelerator

router = APIRouter(prefix="/accelerator", tags=["accelerators"])


@router.post("", response_model=AcceleratorResponse, status_code=status.HTTP_201_CREATED)
async def create_accelerator(db: DbDep, data: AcceleratorCreate) -> Accelerator:
    """Create a new accelerator."""
    accelerator = Accelerator(**data.model_dump())
    db.add(accelerator)
    await db.commit()
    await db.refresh(accelerator)
    return accelerator


@router.get("", response_model=AcceleratorListResponse)
async def list_accelerators(
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("roi_score", enum=["roi_score", "name", "survival_rate_3yr"]),
) -> AcceleratorListResponse:
    """List all accelerators with pagination and sorting."""
    count_result = await db.execute(select(func.count()).select_from(Accelerator))
    total = count_result.scalar()

    offset = (page - 1) * page_size

    # Sort by specified field
    if sort_by == "name":
        order_by = Accelerator.name
    elif sort_by == "roi_score":
        order_by = Accelerator.roi_score.desc()
    elif sort_by == "survival_rate_3yr":
        order_by = Accelerator.survival_rate_3yr.desc()
    else:
        order_by = Accelerator.roi_score.desc()

    result = await db.execute(
        select(Accelerator)
        .order_by(order_by)
        .offset(offset)
        .limit(page_size)
    )
    accelerators = result.scalars().all()

    return AcceleratorListResponse(
        items=accelerators,
        total=total,
    )


@router.get("/{accelerator_id}", response_model=AcceleratorResponse)
async def get_accelerator(accelerator_id: UUID, db: DbDep) -> Accelerator:
    """Get an accelerator by ID."""
    return await get_accelerator_or_404(db, accelerator_id)


@router.delete("/{accelerator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_accelerator(accelerator_id: UUID, db: DbDep) -> None:
    """Delete an accelerator."""
    accelerator = await get_accelerator_or_404(db, accelerator_id)
    await db.delete(accelerator)
    await db.commit()


@router.get("/{accelerator_id}/ranking", response_model=AcceleratorBotOutput)
async def get_accelerator_ranking(accelerator_id: UUID, db: DbDep) -> AcceleratorBotOutput:
    """Get ROI ranking analysis for an accelerator."""
    accelerator = await get_accelerator_or_404(db, accelerator_id)

    bot = AcceleratorBot()

    # Calculate ROI score
    metrics = {
        "follow_on_funding_rate": accelerator.follow_on_rate or 0,
        "median_time_to_series_a_months": accelerator.median_time_to_series_a_months or 36,
        "survival_rate_3yr": accelerator.survival_rate_3yr or 0,
        "unicorn_rate": accelerator.unicorn_rate or 0,
        "shutdown_rate": accelerator.shutdown_rate or 0,
    }

    roi_score = bot.compute_roi_score(metrics, accelerator.cohort_count)
    normalized = bot.normalize_metrics(metrics)
    confidence = bot.confidence_interval(
        int((accelerator.survival_rate_3yr or 0) * accelerator.cohort_count),
        accelerator.cohort_count,
    )

    return AcceleratorBotOutput(
        accelerator_id=accelerator_id,
        name=accelerator.name,
        roi_score=roi_score,
        global_rank=0,  # Would need to calculate against all accelerators
        industry_rank=0,
        geo_rank=0,
        normalized_metrics=normalized,
        confidence_interval=confidence,
        peer_comparison=[],
        computed_at=accelerator.updated_at,
    )


@router.get("/rankings/top", response_model=AcceleratorListResponse)
async def get_top_accelerators(
    db: DbDep,
    limit: int = Query(10, ge=1, le=50),
) -> AcceleratorListResponse:
    """Get top accelerators by ROI score."""
    result = await db.execute(
        select(Accelerator)
        .where(Accelerator.roi_score.isnot(None))
        .order_by(Accelerator.roi_score.desc())
        .limit(limit)
    )
    accelerators = result.scalars().all()

    return AcceleratorListResponse(
        items=accelerators,
        total=len(accelerators),
    )
