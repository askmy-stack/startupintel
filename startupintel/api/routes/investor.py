"""Investor API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func

from startupintel.api.dependencies import DbDep, get_investor_or_404
from startupintel.api.schemas import (
    InvestorCreate,
    InvestorResponse,
    InvestorListResponse,
    InvestorBotOutput,
)
from startupintel.bots.investor_bot import InvestorBot
from startupintel.db.models import Investor
from startupintel.events.producer import InMemoryEventProducer
from startupintel.llm.client import get_llm_client
from startupintel.rag.retriever import get_retriever

router = APIRouter(prefix="/investor", tags=["investors"])


@router.post("", response_model=InvestorResponse, status_code=status.HTTP_201_CREATED)
async def create_investor(db: DbDep, data: InvestorCreate) -> Investor:
    """Create a new investor."""
    investor = Investor(**data.model_dump())
    db.add(investor)
    await db.commit()
    await db.refresh(investor)
    return investor


@router.get("", response_model=InvestorListResponse)
async def list_investors(
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> InvestorListResponse:
    """List all investors with pagination."""
    count_result = await db.execute(select(func.count()).select_from(Investor))
    total = count_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Investor)
        .order_by(Investor.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    investors = result.scalars().all()

    return InvestorListResponse(
        items=investors,
        total=total,
    )


@router.get("/{investor_id}", response_model=InvestorResponse)
async def get_investor(investor_id: UUID, db: DbDep) -> Investor:
    """Get an investor by ID."""
    return await get_investor_or_404(db, investor_id)


@router.delete("/{investor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investor(investor_id: UUID, db: DbDep) -> None:
    """Delete an investor."""
    investor = await get_investor_or_404(db, investor_id)
    await db.delete(investor)
    await db.commit()


@router.get("/{investor_id}/network", response_model=InvestorBotOutput)
async def get_investor_network(investor_id: UUID, db: DbDep) -> InvestorBotOutput:
    """Get network analysis for an investor."""
    investor = await get_investor_or_404(db, investor_id)

    bot = InvestorBot(
        db=db,
        llm_client=get_llm_client(),
        rag_retriever=get_retriever(),
        producer=InMemoryEventProducer(),
    )

    result = await bot.run(investor_id)

    # Get co-investor graph from raw signals
    raw = result.raw_signals
    deals = raw.get("deals", [])
    co_investor_graph = bot.project_co_investor_graph(deals)

    return InvestorBotOutput(
        startup_id=investor_id,
        score=result.score,
        network_metrics={
            "betweenness": result.signal_breakdown.get("betweenness", 0),
            "eigenvector": result.signal_breakdown.get("eigenvector", 0),
            "diversity": result.signal_breakdown.get("diversity", 0),
            "value_add_proxy": result.signal_breakdown.get("value_add_proxy", 0),
        },
        diversity_score=bot.diversity_score(raw.get("portfolio_labels", [])),
        co_investor_graph=co_investor_graph,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at,
    )
