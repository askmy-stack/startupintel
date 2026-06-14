"""File upload and management routes."""

from __future__ import annotations

import logging
import mimetypes
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.api.dependencies import get_db
from startupintel.api.dependencies.auth import get_current_user
from startupintel.config import get_settings
from startupintel.db.models import UploadedFile, User
from startupintel.utils.storage import (
    FileInfo,
    generate_thumbnail,
    get_storage_backend,
    scan_file_with_clamav,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_CATEGORIES = ["termsheet", "pitch_deck", "logo", "document", "report", "other"]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    category: Annotated[str, Form()] = "document",
    description: Annotated[str | None, Form()] = None,
    startup_id: Annotated[UUID | None, Form()] = None,
    generate_thumbnail_flag: Annotated[bool, Form()] = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a file with virus scanning and optional thumbnail generation."""
    settings = get_settings()

    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Allowed: {', '.join(ALLOWED_CATEGORIES)}",
        )

    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    allowed_types = settings.allowed_file_types.split(",")
    filename = file.filename or "unknown"
    ext = f".{filename.split('.')[-1].lower()}" if "." in filename else ""
    if ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type not allowed. Allowed: {settings.allowed_file_types}",
        )

    file_buffer = BytesIO(content)
    scan_result = await scan_file_with_clamav(file_buffer)

    storage = get_storage_backend()
    file_buffer.seek(0)
    content_type = (
        file.content_type
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    file_info: FileInfo = await storage.upload(
        file_data=file_buffer,
        filename=filename,
        content_type=content_type,
        metadata={
            "uploaded_by": str(user.id),
            "organization_id": str(user.organization_id),
            "category": category,
        },
    )

    thumbnail_path = None
    if generate_thumbnail_flag and content_type.startswith("image/"):
        try:
            file_buffer.seek(0)
            thumb_buffer = await generate_thumbnail(file_buffer, size=(300, 300))
            thumb_info = await storage.upload(
                file_data=thumb_buffer,
                filename=f"thumb_{filename}",
                content_type="image/jpeg",
                metadata={"thumbnail_of": str(file_info.id)},
            )
            thumbnail_path = thumb_info.storage_path
        except Exception as exc:
            logger.warning("Thumbnail generation failed: %s", exc)

    access_url = await storage.get_url(file_info.storage_path, expiration=3600)

    uploaded_file = UploadedFile(
        organization_id=user.organization_id,
        user_id=user.id,
        startup_id=startup_id,
        original_filename=filename,
        storage_path=file_info.storage_path,
        content_type=content_type,
        size_bytes=file_info.size,
        checksum_sha256=file_info.checksum,
        file_category=category,
        file_description=description,
        virus_scan_status="clean" if scan_result["is_clean"] else "infected",
        virus_scan_details=scan_result,
        thumbnail_path=thumbnail_path,
        access_url=access_url,
        access_url_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    db.add(uploaded_file)
    await db.commit()
    await db.refresh(uploaded_file)

    return {
        "id": str(uploaded_file.id),
        "filename": uploaded_file.original_filename,
        "category": uploaded_file.file_category,
        "size_bytes": uploaded_file.size_bytes,
        "content_type": uploaded_file.content_type,
        "virus_scan_status": uploaded_file.virus_scan_status,
        "thumbnail_available": thumbnail_path is not None,
        "access_url": access_url,
        "expires_at": uploaded_file.access_url_expires_at.isoformat(),
        "uploaded_at": uploaded_file.uploaded_at.isoformat(),
    }


@router.get("/")
async def list_files(
    category: str | None = Query(None),
    startup_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List non-deleted files for the caller's organization."""
    stmt = select(UploadedFile).where(
        UploadedFile.organization_id == user.organization_id,
        UploadedFile.deleted_at.is_(None),
    )
    if category:
        stmt = stmt.where(UploadedFile.file_category == category)
    if startup_id:
        stmt = stmt.where(UploadedFile.startup_id == startup_id)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(UploadedFile.uploaded_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    files = result.scalars().all()

    storage = get_storage_backend()
    file_list = []
    for f in files:
        if not f.access_url or (
            f.access_url_expires_at and f.access_url_expires_at < datetime.now(UTC)
        ):
            f.access_url = await storage.get_url(f.storage_path, expiration=3600)
            f.access_url_expires_at = datetime.now(UTC) + timedelta(hours=1)

        file_list.append(
            {
                "id": str(f.id),
                "filename": f.original_filename,
                "category": f.file_category,
                "description": f.file_description,
                "size_bytes": f.size_bytes,
                "content_type": f.content_type,
                "virus_scan_status": f.virus_scan_status,
                "thumbnail_available": f.thumbnail_path is not None,
                "access_url": f.access_url,
                "expires_at": (
                    f.access_url_expires_at.isoformat()
                    if f.access_url_expires_at
                    else None
                ),
                "startup_id": str(f.startup_id) if f.startup_id else None,
                "uploaded_at": f.uploaded_at.isoformat(),
            }
        )

    await db.commit()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return {
        "items": file_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a stored file back to the caller."""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.organization_id == user.organization_id,
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record or not file_record.is_accessible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or not accessible",
        )

    storage = get_storage_backend()
    file_buffer = await storage.download(file_record.storage_path)

    return StreamingResponse(
        file_buffer,
        media_type=file_record.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{file_record.original_filename}"'
            ),
        },
    )


@router.get("/{file_id}/thumbnail")
async def get_thumbnail(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a stored thumbnail back to the caller."""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.organization_id == user.organization_id,
            UploadedFile.thumbnail_path.isnot(None),
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found",
        )

    storage = get_storage_backend()
    thumb_buffer = await storage.download(file_record.thumbnail_path)

    return StreamingResponse(thumb_buffer, media_type="image/jpeg")


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a file (owner or admin only)."""
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.organization_id == user.organization_id,
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if file_record.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this file",
        )

    file_record.deleted_at = datetime.now(UTC)
    await db.commit()
