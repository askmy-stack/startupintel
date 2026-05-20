"""File storage utilities for S3/MinIO/local storage."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

import httpx
from startupintel.config import get_settings


@dataclass
class FileInfo:
    """File metadata."""
    id: UUID
    filename: str
    content_type: str
    size: int
    checksum: str
    storage_path: str
    url: str
    created_at: datetime
    metadata: dict


class StorageBackend:
    """Abstract storage backend."""
    
    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> FileInfo:
        raise NotImplementedError
    
    async def download(self, storage_path: str) -> BytesIO:
        raise NotImplementedError
    
    async def delete(self, storage_path: str) -> bool:
        raise NotImplementedError
    
    async def get_url(self, storage_path: str, expiration: int = 3600) -> str:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: str = "./data/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.public_url_prefix = "/uploads"
    
    def _get_storage_path(self, file_id: UUID, filename: str) -> str:
        """Generate storage path with date-based directory structure."""
        now = datetime.now(UTC)
        date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"
        safe_filename = f"{file_id}_{filename.replace(' ', '_')}"
        return f"{date_path}/{safe_filename}"
    
    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> FileInfo:
        file_id = uuid4()
        storage_path = self._get_storage_path(file_id, filename)
        
        # Create directory
        full_path = self.base_path / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and save file
        file_data.seek(0)
        content = file_data.read()
        checksum = hashlib.sha256(content).hexdigest()
        
        with open(full_path, "wb") as f:
            f.write(content)
        
        # Detect content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"
        
        return FileInfo(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size=len(content),
            checksum=checksum,
            storage_path=storage_path,
            url=f"{self.public_url_prefix}/{storage_path}",
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )
    
    async def download(self, storage_path: str) -> BytesIO:
        full_path = self.base_path / storage_path
        with open(full_path, "rb") as f:
            return BytesIO(f.read())
    
    async def delete(self, storage_path: str) -> bool:
        full_path = self.base_path / storage_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    async def get_url(self, storage_path: str, expiration: int = 3600) -> str:
        return f"{self.public_url_prefix}/{storage_path}"


class S3StorageBackend(StorageBackend):
    """S3/MinIO storage backend."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bucket = self.settings.storage_bucket
        
        import boto3
        from botocore.config import Config
        
        # Configure S3 client
        session_kwargs = {
            "aws_access_key_id": self.settings.s3_access_key,
            "aws_secret_access_key": self.settings.s3_secret_key,
            "region_name": self.settings.s3_region,
        }
        
        client_kwargs = {
            "config": Config(max_pool_connections=50),
        }
        
        # Use custom endpoint for MinIO
        if self.settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = self.settings.s3_endpoint_url
        
        session = boto3.session.Session(**session_kwargs)
        self.client = session.client("s3", **client_kwargs)
    
    def _get_storage_path(self, file_id: UUID, filename: str) -> str:
        """Generate storage path with date-based directory structure."""
        now = datetime.now(UTC)
        date_path = f"{now.year}/{now.month:02d}/{now.day:02d}"
        safe_filename = f"{file_id}_{filename.replace(' ', '_')}"
        return f"{date_path}/{safe_filename}"
    
    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> FileInfo:
        file_id = uuid4()
        storage_path = self._get_storage_path(file_id, filename)
        
        # Read content
        file_data.seek(0)
        content = file_data.read()
        checksum = hashlib.sha256(content).hexdigest()
        
        # Detect content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"
        
        # Upload to S3
        extra_args = {
            "ContentType": content_type,
            "Metadata": {
                "original-filename": filename,
                "checksum-sha256": checksum,
                "upload-timestamp": datetime.now(UTC).isoformat(),
                **{f"meta-{k}": str(v) for k, v in (metadata or {}).items()},
            },
        }
        
        self.client.put_object(
            Bucket=self.bucket,
            Key=storage_path,
            Body=content,
            **extra_args,
        )
        
        return FileInfo(
            id=file_id,
            filename=filename,
            content_type=content_type,
            size=len(content),
            checksum=checksum,
            storage_path=storage_path,
            url=f"s3://{self.bucket}/{storage_path}",
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )
    
    async def download(self, storage_path: str) -> BytesIO:
        response = self.client.get_object(Bucket=self.bucket, Key=storage_path)
        return BytesIO(response["Body"].read())
    
    async def delete(self, storage_path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_path)
            return True
        except Exception:
            return False
    
    async def get_url(self, storage_path: str, expiration: int = 3600) -> str:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_path},
            ExpiresIn=expiration,
        )
        return url


def get_storage_backend() -> StorageBackend:
    """Get configured storage backend."""
    settings = get_settings()
    
    if settings.storage_provider in ("s3", "minio"):
        return S3StorageBackend()
    return LocalStorageBackend()


# Virus scanning (ClamAV integration)
async def scan_file_with_clamav(file_data: BinaryIO) -> dict:
    """Scan file with ClamAV."""
    file_data.seek(0)
    
    try:
        import clamd
        cd = clamd.ClamdUnixSocket()
        scan_result = cd.scan_stream(file_data.read())
        
        if scan_result:
            return {
                "is_clean": False,
                "threats": [r for r in scan_result.values()],
            }
        
        return {"is_clean": True, "threats": []}
    except Exception as e:
        # If ClamAV is not available, log warning but allow file
        import logging
        logging.getLogger(__name__).warning(f"Virus scan unavailable: {e}")
        return {"is_clean": True, "threats": [], "scan_error": str(e)}


async def scan_file_with_virustotal(file_hash: str, api_key: str) -> dict:
    """Check file hash against VirusTotal."""
    if not api_key:
        return {"skipped": True, "reason": "No API key configured"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.virustotal.com/api/v3/files/{file_hash}",
            headers={"x-apikey": api_key},
        )
        
        if response.status_code == 404:
            return {"not_found": True}
        
        if response.status_code == 200:
            data = response.json()
            stats = data["data"]["attributes"]["last_analysis_stats"]
            return {
                "found": True,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "undetected": stats.get("undetected", 0),
                "harmless": stats.get("harmless", 0),
            }
        
        return {"error": f"VirusTotal API error: {response.status_code}"}


# Thumbnail generation for images
async def generate_thumbnail(file_data: BinaryIO, size: tuple = (200, 200)) -> BytesIO:
    """Generate thumbnail from image."""
    from PIL import Image
    
    file_data.seek(0)
    img = Image.open(file_data)
    img.thumbnail(size)
    
    output = BytesIO()
    img.save(output, format="JPEG", quality=85)
    output.seek(0)
    
    return output
