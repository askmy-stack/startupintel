"""Investor CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from startupintel.api.dependencies import DbDep, get_investor_or_404
from startupintel.api.schemas import (
    InvestorCreate,
    InvestorListResponse,
    InvestorResponse,
)
from startupintel.db.models import Investor

router = APIRouter(prefix="/investor", tags=["investor"])


@router.post("", response_model=InvestorResponse, status_code=status.HTTP_201_CREATED)
async def create_investor(db: DbDep, data: InvestorCreate) -> Investor:
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
    total = await db.scalar(select(func.count()).select_from(Investor))
    result = await db.execute(
        select(Investor)
        .order_by(Investor.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return InvestorListResponse(items=list(result.scalars().all()), total=total or 0)


@router.get("/{investor_id}", response_model=InvestorResponse)
async def get_investor(investor_id: UUID, db: DbDep) -> Investor:
    return await get_investor_or_404(db, investor_id)


@router.delete("/{investor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investor(investor_id: UUID, db: DbDep) -> None:
    investor = await get_investor_or_404(db, investor_id)
    await db.delete(investor)
    await db.commit()
