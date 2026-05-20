"""Authentication and user management schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# ========== Organization Schemas ==========

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(None, max_length=1000)
    website: str | None = Field(None, max_length=255)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=500)
    settings: dict | None = None
    is_active: bool | None = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    logo_url: str | None
    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== User Schemas ==========

class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.ANALYST
    organization_id: UUID

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None
    settings: dict | None = None


class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None
    organization_id: UUID
    organization: OrganizationResponse | None
    full_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========== Authentication Schemas ==========

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenPayload(BaseModel):
    sub: UUID  # user_id
    org: UUID  # organization_id
    role: UserRole
    type: TokenType
    exp: datetime
    iat: datetime
    jti: UUID  # token ID for revocation


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ========== API Key Schemas ==========

class APIKeyScope(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[APIKeyScope] = [APIKeyScope.READ]
    rate_limit_per_minute: int = Field(60, ge=1, le=10000)
    expires_days: int | None = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    # NOTE: The actual key is only shown once on creation
    scopes: list[APIKeyScope]
    rate_limit_per_minute: int
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Response that includes the actual API key (only shown once)."""
    api_key: str  # Full API key - only returned on creation


class APIKeyListResponse(BaseModel):
    items: list[APIKeyResponse]
    total: int


# ========== Permission Check Helpers ==========

def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """Check if user role has required permission level."""
    hierarchy = {
        UserRole.VIEWER: 0,
        UserRole.ANALYST: 1,
        UserRole.ADMIN: 2,
    }
    return hierarchy.get(user_role, 0) >= hierarchy.get(required_role, 0)
