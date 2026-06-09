"""Authentication and user management routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from startupintel.api.dependencies.auth import (
    get_current_user,
    require_admin,
    get_db,
)
from startupintel.api.schemas.auth import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    LoginRequest,
    OrganizationResponse,
    OrganizationUpdate,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRole,
    UserUpdate,
)
from startupintel.db.models import APIKey, Organization, RefreshToken, User
from startupintel.utils.auth import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ========== Authentication ==========

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return access/refresh tokens."""
    # Find user by email
    stmt = select(User).where(User.email == request.email).options(
        select(User).selectinload(User.organization)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # Verify password
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    # Create tokens
    access_token, _ = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
    )
    refresh_token, token_hash = create_refresh_token(user_id=user.id)
    
    # Store refresh token
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(db_refresh)
    await db.commit()
    
    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60,  # 30 minutes
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    from startupintel.utils.auth import decode_token
    
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user_id = UUID(payload.get("sub"))
    
    # Verify token hash in database
    import hashlib
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    
    stmt = (
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.user_id == user_id)
        .where(RefreshToken.revoked_at.is_(None))
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    
    if not db_token or db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired",
        )
    
    # Get user
    user_stmt = select(User).where(User.id == user_id).options(
        select(User).selectinload(User.organization)
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one()
    
    # Create new tokens
    access_token, _ = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
    )
    new_refresh_token, new_token_hash = create_refresh_token(user_id=user.id)
    
    # Revoke old token and create new one
    db_token.revoked_at = datetime.now(UTC)
    
    new_db_token = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(new_db_token)
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=30 * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke refresh token (logout)."""
    import hashlib
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    
    if db_token:
        db_token.revoked_at = datetime.now(UTC)
        await db.commit()
    
    return {"message": "Successfully logged out"}


# ========== User Management ==========

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user (creates organization if needed)."""
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create organization
    org_slug = request.email.split("@")[0].lower().replace(".", "-")
    org = Organization(
        name=f"{request.first_name or request.email}'s Organization",
        slug=org_slug,
    )
    db.add(org)
    await db.flush()  # Get org ID
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=UserRole.ADMIN,  # First user is admin
        organization_id=org.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Get current user profile."""
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user profile."""
    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name
    if request.settings is not None:
        user.settings.update(request.settings)
    
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/me/password")
async def change_password(
    request: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change user password."""
    # Verify current password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    
    # Revoke all refresh tokens for security
    for token in user.refresh_tokens:
        if not token.is_revoked:
            token.revoked_at = datetime.now(UTC)
    
    await db.commit()
    
    return {"message": "Password changed successfully. Please log in again."}


# ========== Organization Management ==========

@router.get("/organization", response_model=OrganizationResponse)
async def get_organization(user: User = Depends(get_current_user)) -> OrganizationResponse:
    """Get current user's organization."""
    return OrganizationResponse.model_validate(user.organization)


@router.put("/organization", response_model=OrganizationResponse)
async def update_organization(
    request: OrganizationUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Update organization (admin only)."""
    org = user.organization
    
    if request.name is not None:
        org.name = request.name
    if request.description is not None:
        org.description = request.description
    if request.website is not None:
        org.website = request.website
    if request.logo_url is not None:
        org.logo_url = request.logo_url
    if request.settings is not None:
        org.settings.update(request.settings)
    if request.is_active is not None:
        org.is_active = request.is_active
    
    await db.commit()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)


# ========== User Management (Admin Only) ==========

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List users in organization (admin only)."""
    from sqlalchemy import func
    
    # Get organization users
    stmt = select(User).where(User.organization_id == user.organization_id)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user in organization (admin only)."""
    # Check email exists
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user in same organization
    new_user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role.value,
        organization_id=admin.organization_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse.model_validate(new_user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user (admin only)."""
    stmt = select(User).where(
        User.id == user_id,
        User.organization_id == admin.organization_id,
    )
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if request.first_name is not None:
        target_user.first_name = request.first_name
    if request.last_name is not None:
        target_user.last_name = request.last_name
    if request.role is not None:
        target_user.role = request.role.value
    if request.is_active is not None:
        target_user.is_active = request.is_active
    if request.settings is not None:
        target_user.settings.update(request.settings)
    
    await db.commit()
    await db.refresh(target_user)
    return UserResponse.model_validate(target_user)


# ========== API Key Management ==========

@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreateResponse:
    """Create a new API key for user/organization."""
    full_key, prefix, key_hash = generate_api_key()
    
    api_key_obj = APIKey(
        organization_id=user.organization_id,
        user_id=user.id,
        name=request.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=[s.value for s in request.scopes],
        rate_limit_per_minute=request.rate_limit_per_minute,
    )
    
    if request.expires_days:
        api_key_obj.expires_at = datetime.now(UTC) + timedelta(days=request.expires_days)
    
    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)
    
    # Build response with full key (only shown once)
    response_data = APIKeyResponse.model_validate(api_key_obj).model_dump()
    response_data["api_key"] = full_key
    
    return APIKeyCreateResponse(**response_data)


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyListResponse:
    """List API keys for current user."""
    stmt = select(APIKey).where(
        APIKey.organization_id == user.organization_id
    ).order_by(APIKey.created_at.desc())
    
    result = await db.execute(stmt)
    api_keys = result.scalars().all()
    
    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in api_keys],
        total=len(api_keys),
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke an API key."""
    stmt = select(APIKey).where(
        APIKey.id == key_id,
        APIKey.organization_id == user.organization_id,
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Only admin or key owner can revoke
    if user.role != UserRole.ADMIN.value and api_key.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke another user's API key",
        )
    
    api_key.is_active = False
    await db.commit()
    
    return {"message": "API key revoked"}
