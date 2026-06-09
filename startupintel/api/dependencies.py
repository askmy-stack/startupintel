"""API dependencies for StartupIntel."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, UTC
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.config import get_settings
from startupintel.db.models import Startup, Investor, Accelerator
from startupintel.db.postgres import get_session
from startupintel.db.redis import get_redis
from startupintel.db.neo4j import get_neo4j_driver
from startupintel.llm.client import get_llm_client, BaseLLMClient
from startupintel.rag.retriever import get_retriever, FAISSRetriever, EmptyRetriever

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_session():
        yield session


async def get_redis_client():
    """Get Redis client."""
    return get_redis()


async def get_neo4j():
    """Get Neo4j driver."""
    return get_neo4j_driver()


async def get_llm() -> BaseLLMClient:
    """Get LLM client."""
    return get_llm_client()


async def get_rag() -> FAISSRetriever | EmptyRetriever:
    """Get RAG retriever."""
    return get_retriever()


DbDep = Annotated[AsyncSession, Depends(get_db)]

# For Redis, Neo4j, LLM, RAG - use simple Depends() in routes rather than Annotated
def RedisDep():
    return Depends(get_redis_client)

def Neo4jDep():
    return Depends(get_neo4j)

def LLMDep():
    return Depends(get_llm)

def RAGDep():
    return Depends(get_rag)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    settings = get_settings()
    return jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
) -> dict:
    """Get current authenticated user from JWT token."""
    if not credentials:
        # Allow unauthenticated access for now (development)
        return {"user_id": "anonymous", "role": "guest"}

    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, settings.api_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return {"user_id": user_id, "role": payload.get("role", "user")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


AuthDep = Annotated[dict, Depends(get_current_user)]


async def get_startup_or_404(db: DbDep, startup_id: UUID) -> Startup:
    """Get startup by ID or raise 404."""
    startup = await db.get(Startup, startup_id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup {startup_id} not found",
        )
    return startup


async def get_investor_or_404(db: DbDep, investor_id: UUID) -> Investor:
    """Get investor by ID or raise 404."""
    investor = await db.get(Investor, investor_id)
    if not investor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investor {investor_id} not found",
        )
    return investor


async def get_accelerator_or_404(db: DbDep, accelerator_id: UUID) -> Accelerator:
    """Get accelerator by ID or raise 404."""
    accelerator = await db.get(Accelerator, accelerator_id)
    if not accelerator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accelerator {accelerator_id} not found",
        )
    return accelerator


# ========== Rate Limiting ==========

# Simple in-memory rate limiter (use Redis in production for distributed rate limiting)
_rate_limit_store: dict[str, tuple[list[datetime], int]] = {}


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window = timedelta(minutes=1)
    
    async def check_rate_limit(self, key: str) -> tuple[bool, int, int]:
        """Check if request is within rate limit.
        
        Returns: (allowed, remaining, reset_in_seconds)
        """
        now = datetime.now(UTC)
        
        if key not in _rate_limit_store:
            _rate_limit_store[key] = ([now], 1)
            return True, self.requests_per_minute - 1, 60
        
        requests, _ = _rate_limit_store[key]
        
        # Remove expired requests
        cutoff = now - self.window
        requests = [r for r in requests if r > cutoff]
        
        if len(requests) >= self.requests_per_minute:
            reset_in = int((requests[0] + self.window - now).total_seconds())
            _rate_limit_store[key] = (requests, len(requests))
            return False, 0, max(reset_in, 1)
        
        requests.append(now)
        _rate_limit_store[key] = (requests, len(requests))
        remaining = self.requests_per_minute - len(requests)
        
        return True, remaining, 60


async def rate_limit_dependency(
    request: Request,
    requests_per_minute: int = 60,
) -> None:
    """Rate limiting dependency for FastAPI endpoints.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(RateLimiter(requests_per_minute=30))])
    """
    # Create key from client IP + path
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    
    limiter = RateLimiter(requests_per_minute=requests_per_minute)
    allowed, remaining, reset_in = await limiter.check_rate_limit(key)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
            headers={
                "X-RateLimit-Limit": str(requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_in),
                "Retry-After": str(reset_in),
            },
        )
    
    # Store rate limit info in request state for response headers
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_limit = requests_per_minute
