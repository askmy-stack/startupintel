"""Term sheet analysis CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from startupintel.api.dependencies import DbDep
from startupintel.api.schemas import (
    TermSheetCreate,
    TermSheetListResponse,
    TermSheetResponse,
)
from startupintel.db.models import TermSheetAnalysis

router = APIRouter(prefix="/termsheet", tags=["termsheet"])


async def _get_or_404(db: DbDep, termsheet_id: UUID) -> TermSheetAnalysis:
    analysis = await db.get(TermSheetAnalysis, termsheet_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term sheet analysis {termsheet_id} not found",
        )
    return analysis


@router.post("", response_model=TermSheetResponse, status_code=status.HTTP_201_CREATED)
async def create_termsheet(db: DbDep, data: TermSheetCreate) -> TermSheetAnalysis:
    analysis = TermSheetAnalysis(**data.model_dump())
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


@router.get("", response_model=TermSheetListResponse)
async def list_termsheets(
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TermSheetListResponse:
    total = await db.scalar(select(func.count()).select_from(TermSheetAnalysis))
    result = await db.execute(
        select(TermSheetAnalysis)
        .order_by(TermSheetAnalysis.analyzed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return TermSheetListResponse(items=list(result.scalars().all()), total=total or 0)


@router.get("/{termsheet_id}", response_model=TermSheetResponse)
async def get_termsheet(termsheet_id: UUID, db: DbDep) -> TermSheetAnalysis:
    return await _get_or_404(db, termsheet_id)


@router.delete("/{termsheet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_termsheet(termsheet_id: UUID, db: DbDep) -> None:
    analysis = await _get_or_404(db, termsheet_id)
    await db.delete(analysis)
    await db.commit()
