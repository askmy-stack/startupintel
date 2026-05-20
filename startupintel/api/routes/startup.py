"""Startup API routes with CRUD and bot integration."""

import logging
from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

logger = logging.getLogger(__name__)
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from startupintel.api.dependencies import DbDep, get_startup_or_404
from startupintel.api.schemas import (
    StartupCreate,
    StartupResponse,
    StartupUpdate,
    StartupListResponse,
    StartupSummary,
    StartupSearchRequest,
    StartupSearchResponse,
    RunwayBotOutput,
    ObituaryBotOutput,
    PMFBotOutput,
    PivotBotOutput,
    AcquiBotOutput,
    BotScoreListResponse,
    BotRunResponse,
)
from startupintel.bots.runway_bot import RunwayBot
from startupintel.bots.obituary_bot import ObituaryBot
from startupintel.bots.pmf_bot import PMFBot
from startupintel.bots.pivot_bot import PivotBot
from startupintel.bots.acqui_bot import AcquiBot
from startupintel.db.models import Startup, StartupScore
from startupintel.events.producer import InMemoryEventProducer
from startupintel.llm.client import get_llm_client
from startupintel.rag.retriever import get_retriever

router = APIRouter(prefix="/startup", tags=["startups"])


# ========== CRUD Endpoints ==========

@router.post("", response_model=StartupResponse, status_code=status.HTTP_201_CREATED)
async def create_startup(db: DbDep, data: StartupCreate) -> Startup:
    """Create a new startup."""
    startup = Startup(**data.model_dump())
    db.add(startup)
    await db.commit()
    await db.refresh(startup)
    return startup


@router.get("", response_model=StartupListResponse)
async def list_startups(
    db: DbDep,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, name, employee_count, total_funding_usd)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    industry: str | None = Query(None, description="Filter by industry"),
    stage: str | None = Query(None, description="Filter by stage (seed, series_a, series_b, growth)"),
) -> StartupListResponse:
    """List all startups with pagination, sorting, and filtering."""
    # Validate sort_by field
    valid_sort_fields = {"created_at", "name", "employee_count", "total_funding_usd"}
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    # Validate sort_order
    if sort_order.lower() not in {"asc", "desc"}:
        sort_order = "desc"
    
    # Build base query with filters
    stmt = select(Startup)
    if industry:
        stmt = stmt.where(Startup.industry.ilike(f"%{industry}%"))
    if stage:
        stmt = stmt.where(Startup.stage == stage)
    
    # Get total count (with filters applied)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Apply sorting
    sort_column = getattr(Startup, sort_by)
    if sort_order.lower() == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    startups = result.scalars().all()

    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1

    return StartupListResponse(
        items=[StartupSummary(
            id=s.id,
            name=s.name,
            domain=s.domain,
            industry=s.industry,
            stage=s.stage,
            employee_count=s.employee_count,
            total_funding_usd=s.total_funding_usd,
        ) for s in startups],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )


@router.get("/search", response_model=StartupSearchResponse)
async def search_startups(
    db: DbDep,
    query: str | None = None,
    industry: str | None = None,
    stage: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StartupSearchResponse:
    """Search startups by query, industry, or stage."""
    stmt = select(Startup)

    if query:
        stmt = stmt.where(
            Startup.name.ilike(f"%{query}%") | Startup.domain.ilike(f"%{query}%")
        )
    if industry:
        stmt = stmt.where(Startup.industry.ilike(f"%{industry}%"))
    if stage:
        stmt = stmt.where(Startup.stage == stage)

    # Get total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Get results
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Startup.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    startups = result.scalars().all()

    return StartupSearchResponse(
        items=[StartupSummary(
            id=s.id,
            name=s.name,
            domain=s.domain,
            industry=s.industry,
            stage=s.stage,
            employee_count=s.employee_count,
            total_funding_usd=s.total_funding_usd,
        ) for s in startups],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{startup_id}", response_model=StartupResponse)
async def get_startup(startup_id: UUID, db: DbDep) -> Startup:
    """Get a startup by ID."""
    return await get_startup_or_404(db, startup_id)


@router.patch("/{startup_id}", response_model=StartupResponse)
async def update_startup(
    startup_id: UUID,
    data: StartupUpdate,
    db: DbDep,
) -> Startup:
    """Update a startup."""
    startup = await get_startup_or_404(db, startup_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(startup, key, value)

    await db.commit()
    await db.refresh(startup)
    return startup


@router.delete("/{startup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_startup(startup_id: UUID, db: DbDep) -> None:
    """Delete a startup."""
    startup = await get_startup_or_404(db, startup_id)
    await db.delete(startup)
    await db.commit()


# ========== Bot Endpoints ==========

@router.get("/{startup_id}/stress", response_model=RunwayBotOutput)
async def get_runway_stress(startup_id: UUID, db: DbDep) -> RunwayBotOutput:
    """Get runway stress analysis for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = RunwayBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)
    raw = result.raw_signals

    return RunwayBotOutput(
        startup_id=startup_id,
        score=result.score,
        risk_level=bot.risk_level(result.score),
        signal_breakdown=result.signal_breakdown,
        headcount_delta_pct=raw.get("headcount_delta_pct", 0.0),
        job_posting_delta_pct=raw.get("job_posting_delta_pct", 0.0),
        founder_sentiment=raw.get("founder_sentiment", 0.0),
        domain_expiry_days=raw.get("domain_expiry_days", 90.0),
        days_since_funding=raw.get("days_since_funding", 365.0),
        similar_cases=result.similar_cases,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )


@router.get("/{startup_id}/obituary", response_model=ObituaryBotOutput)
async def get_obituary_analysis(startup_id: UUID, db: DbDep) -> ObituaryBotOutput:
    """Get failure pattern analysis for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = ObituaryBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)

    # Get failure pattern info
    pattern, confidence = bot.top_failure_pattern(result.similar_cases)
    taxonomy = bot.taxonomy_breakdown(result.similar_cases)

    return ObituaryBotOutput(
        startup_id=startup_id,
        score=result.score,
        risk_level="high" if result.score > 70 else "medium" if result.score > 40 else "low",
        top_failure_pattern=pattern,
        pattern_confidence=confidence,
        similar_failures=result.similar_cases,
        failure_taxonomy_breakdown=taxonomy,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )


@router.get("/{startup_id}/pmf", response_model=PMFBotOutput)
async def get_pmf_analysis(startup_id: UUID, db: DbDep) -> PMFBotOutput:
    """Get product-market fit analysis for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = PMFBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)

    # Detect changepoint
    history = result.raw_signals.get("score_history", [])
    changepoint, change_date = bot.detect_changepoint(history)

    return PMFBotOutput(
        startup_id=startup_id,
        score=result.score,
        pmf_status=bot.pmf_status(result.score),
        strongest_signal=bot.strongest_signal(result.signal_breakdown),
        weakest_signal=bot.weakest_signal(result.signal_breakdown),
        changepoint_detected=changepoint,
        changepoint_date=change_date,
        signal_breakdown=result.signal_breakdown,
        similar_cases=result.similar_cases,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )


@router.get("/{startup_id}/pivot", response_model=PivotBotOutput)
async def get_pivot_analysis(startup_id: UUID, db: DbDep) -> PivotBotOutput:
    """Get pivot detection analysis for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = PivotBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)
    raw = result.raw_signals

    events = raw.get("pivot_events", [])
    deduped = bot.deduplicate_events(events)

    return PivotBotOutput(
        startup_id=startup_id,
        score=result.score,
        pivot_count=len(deduped),
        primary_pivot_type=bot.primary_pivot_type(deduped),
        pivot_events=[{
            "date": e.get("date"),
            "pivot_type": e.get("pivot_type"),
            "confidence": e.get("confidence"),
            "evidence_summary": e.get("evidence_summary"),
        } for e in deduped[:5]],
        avg_confidence=result.signal_breakdown.get("avg_confidence", 0.0),
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )


@router.get("/{startup_id}/acqui", response_model=AcquiBotOutput)
async def get_acqui_analysis(startup_id: UUID, db: DbDep) -> AcquiBotOutput:
    """Get acqui-hire probability analysis for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = AcquiBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)
    raw = result.raw_signals

    # Get likely acquirers
    acquirers = bot.likely_acquirers()

    return AcquiBotOutput(
        startup_id=startup_id,
        score=result.score,
        probability=result.score / 100.0,
        group_scores=bot.group_scores(raw),
        feature_importances=bot.feature_importances(raw),
        likely_acquirers=[{
            "acquirer_id": a.get("acquirer_id"),
            "name": a.get("name"),
            "domain": a.get("domain"),
            "fit_score": a.get("fit_score"),
            "tech_overlap": a.get("tech_overlap"),
            "team_fit": a.get("team_fit"),
            "network_overlap": a.get("network_overlap"),
            "rationale": a.get("rationale"),
        } for a in acquirers],
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )


# ========== Score History ==========

@router.get("/{startup_id}/scores", response_model=BotScoreListResponse)
async def get_startup_scores(
    startup_id: UUID,
    db: DbDep,
    bot_name: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> BotScoreListResponse:
    """Get score history for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    stmt = (
        select(StartupScore)
        .where(StartupScore.startup_id == startup_id)
        .order_by(StartupScore.computed_at.desc())
        .limit(limit)
    )

    if bot_name:
        stmt = stmt.where(StartupScore.bot_name == bot_name)

    result = await db.execute(stmt)
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


@router.post("/{startup_id}/run/{bot_name}", response_model=BotRunResponse)
async def run_bot(
    startup_id: UUID,
    bot_name: str,
    db: DbDep,
) -> BotRunResponse:
    """Manually run a bot for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    # Map bot name to class
    bot_classes = {
        "runway": RunwayBot,
        "obituary": ObituaryBot,
        "pmf": PMFBot,
        "pivot": PivotBot,
        "acqui": AcquiBot,
    }

    if bot_name not in bot_classes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown bot: {bot_name}. Available: {list(bot_classes.keys())}",
        )

    bot_class = bot_classes[bot_name]
    bot = bot_class(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(startup_id)

    return BotRunResponse(
        startup_id=startup_id,
        bot_name=bot_name,
        score=result.score,
        status="completed",
        computed_at=result.computed_at,
    )


# ========== Batch Operations ==========

from pydantic import BaseModel as PydanticBaseModel
from fastapi import BackgroundTasks

class BatchBotRequest(PydanticBaseModel):
    """Request for batch bot analysis."""
    startup_ids: list[UUID]
    bot_names: list[str] = ["runway", "obituary", "pmf"]
    notify_webhook: str | None = None


class BatchBotResult(PydanticBaseModel):
    """Result from a single bot run in batch."""
    startup_id: UUID
    bot_name: str
    status: str
    score: float | None = None
    error: str | None = None


class BatchBotResponse(PydanticBaseModel):
    """Response for batch bot analysis."""
    job_id: str
    total_tasks: int
    completed: int
    failed: int
    results: list[BatchBotResult]
    started_at: datetime
    completed_at: datetime | None = None


@router.post("/batch/analyze", response_model=BatchBotResponse)
async def batch_analyze(
    request: BatchBotRequest,
    db: DbDep,
    background_tasks: BackgroundTasks,
) -> BatchBotResponse:
    """Run bot analysis on multiple startups in batch.
    
    This runs analyses in parallel for better performance.
    Results are returned immediately (synchronous) or can be sent to webhook.
    """
    from datetime import UTC
    import asyncio
    from uuid import uuid4
    
    job_id = str(uuid4())
    started_at = datetime.now(UTC)
    
    total_tasks = len(request.startup_ids) * len(request.bot_names)
    results: list[BatchBotResult] = []
    
    # Map bot names to classes
    bot_classes = {
        "runway": RunwayBot,
        "obituary": ObituaryBot,
        "pmf": PMFBot,
        "pivot": PivotBot,
        "acqui": AcquiBot,
    }
    
    async def run_single_bot(startup_id: UUID, bot_name: str) -> BatchBotResult:
        """Run a single bot and return result."""
        try:
            if bot_name not in bot_classes:
                return BatchBotResult(
                    startup_id=startup_id,
                    bot_name=bot_name,
                    status="error",
                    error=f"Unknown bot: {bot_name}",
                )
            
            # Check startup exists
            startup = await db.get(Startup, startup_id)
            if not startup:
                return BatchBotResult(
                    startup_id=startup_id,
                    bot_name=bot_name,
                    status="error",
                    error=f"Startup not found: {startup_id}",
                )
            
            bot_class = bot_classes[bot_name]
            bot = bot_class(
                db=db,
                llm_client=get_llm_client(),
                rag_retriever=get_retriever(),
                producer=InMemoryEventProducer(),
            )
            
            result = await bot.run(startup_id)
            
            return BatchBotResult(
                startup_id=startup_id,
                bot_name=bot_name,
                status="completed",
                score=result.score,
            )
        except Exception as e:
            return BatchBotResult(
                startup_id=startup_id,
                bot_name=bot_name,
                status="error",
                error=str(e),
            )
    
    # Create all tasks
    tasks = []
    for startup_id in request.startup_ids:
        for bot_name in request.bot_names:
            tasks.append(run_single_bot(startup_id, bot_name))
    
    # Run all tasks concurrently (with limit to avoid overwhelming resources)
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent bot runs
    
    async def run_with_semaphore(task):
        async with semaphore:
            return await task
    
    results = await asyncio.gather(*[run_with_semaphore(t) for t in tasks])
    
    completed = sum(1 for r in results if r.status == "completed")
    failed = sum(1 for r in results if r.status == "error")
    
    # Send webhook notification if configured
    if request.notify_webhook:
        background_tasks.add_task(
            _send_webhook_notification,
            request.notify_webhook,
            job_id,
            results,
        )
    
    return BatchBotResponse(
        job_id=job_id,
        total_tasks=total_tasks,
        completed=completed,
        failed=failed,
        results=results,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


async def _send_webhook_notification(webhook_url: str, job_id: str, results: list) -> None:
    """Send webhook notification with batch results."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                webhook_url,
                json={
                    "job_id": job_id,
                    "status": "completed",
                    "completed_count": len([r for r in results if r.status == "completed"]),
                    "failed_count": len([r for r in results if r.status == "error"]),
                },
                timeout=30.0,
            )
    except Exception as e:
        logger.error(f"Failed to send webhook notification: {e}")

