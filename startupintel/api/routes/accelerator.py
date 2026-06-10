"""Accelerator CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from startupintel.api.dependencies import DbDep, get_accelerator_or_404
from startupintel.api.schemas import (
    AcceleratorCreate,
    AcceleratorListResponse,
    AcceleratorResponse,
)
from startupintel.db.models import Accelerator

router = APIRouter(prefix="/accelerator", tags=["accelerator"])


@router.post("", response_model=AcceleratorResponse, status_code=status.HTTP_201_CREATED)
async def create_accelerator(db: DbDep, data: AcceleratorCreate) -> Accelerator:
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
) -> AcceleratorListResponse:
    total = await db.scalar(select(func.count()).select_from(Accelerator))
    result = await db.execute(
        select(Accelerator)
        .order_by(Accelerator.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AcceleratorListResponse(items=list(result.scalars().all()), total=total or 0)


@router.get("/{accelerator_id}", response_model=AcceleratorResponse)
async def get_accelerator(accelerator_id: UUID, db: DbDep) -> Accelerator:
    return await get_accelerator_or_404(db, accelerator_id)


@router.delete("/{accelerator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_accelerator(accelerator_id: UUID, db: DbDep) -> None:
    accelerator = await get_accelerator_or_404(db, accelerator_id)
    await db.delete(accelerator)
    await db.commit()
