"""Authentication dependencies for FastAPI routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.api.schemas.auth import UserRole, APIKeyScope, has_permission
from startupintel.db.models import APIKey, Organization, User
from startupintel.db.postgres import async_session
from startupintel.utils.auth import decode_token, verify_api_key

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT access token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    stmt = (
        select(User)
        .where(User.id == UUID(user_id))
        .where(User.is_active.is_(True))
        .options(select(User).selectinload(User.organization))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.commit()
    
    return user


async def get_current_user_from_api_key(
    api_key: str | None = Security(api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[User | None, Organization]:
    """Get user/organization from API key.
    
    Returns:
        Tuple of (User | None, Organization)
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Find API key by prefix
    prefix = api_key[:8]
    stmt = select(APIKey).where(APIKey.key_prefix == prefix).where(APIKey.is_active.is_(True))
    result = await db.execute(stmt)
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Verify key hash
    if not verify_api_key(api_key, api_key_obj.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check expiration
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Update last used
    api_key_obj.last_used_at = datetime.now(UTC)
    await db.commit()
    
    # Get organization
    org_stmt = select(Organization).where(Organization.id == api_key_obj.organization_id)
    org_result = await db.execute(org_stmt)
    organization = org_result.scalar_one()
    
    # Get user if associated
    user = None
    if api_key_obj.user_id:
        user_stmt = select(User).where(User.id == api_key_obj.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
    
    return user, organization


# Combined auth - tries bearer token first, then API key
async def get_current_auth(
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[User | None, Organization, list[APIKeyScope]]:
    """Get current authentication from either JWT or API key.
    
    Returns:
        Tuple of (User | None, Organization, scopes)
    """
    if bearer:
        user = await get_current_user(bearer, db)
        return user, user.organization, [APIKeyScope.READ, APIKeyScope.WRITE, APIKeyScope.ADMIN]
    
    if api_key:
        user, org = await get_current_user_from_api_key(api_key, db)
        # Get scopes from API key
        api_key_stmt = select(APIKey).where(APIKey.key_prefix == api_key[:8])
        result = await db.execute(api_key_stmt)
        api_key_obj = result.scalar_one()
        scopes = [APIKeyScope(s) for s in api_key_obj.scopes]
        return user, org, scopes
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or API key)",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


def require_role(required_role: UserRole):
    """Dependency factory to require specific user role."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role.value}",
            )
        return user
    return role_checker


def require_scopes(*required_scopes: APIKeyScope):
    """Dependency factory to require specific API key scopes."""
    async def scope_checker(
        auth: tuple = Depends(get_current_auth)
    ) -> tuple[User | None, Organization, list[APIKeyScope]]:
        user, org, scopes = auth
        
        # Check if all required scopes are present
        missing = set(required_scopes) - set(scopes)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {[s.value for s in missing]}",
            )
        
        return user, org, scopes
    return scope_checker


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN)
require_analyst = require_role(UserRole.ANALYST)
require_write_scope = require_scopes(APIKeyScope.WRITE)
require_admin_scope = require_scopes(APIKeyScope.ADMIN)
