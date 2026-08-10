"""Authentication utilities for password hashing and JWT tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from startupintel.config import get_settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, UUID]:
    """Create a JWT access token.
    
    Returns:
        Tuple of (token, jti) where jti is the unique token ID
    """
    settings = get_settings()
    jti = uuid4()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(jti),
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")
    return encoded_jwt, jti


def create_refresh_token(user_id: UUID, expires_delta: timedelta | None = None) -> tuple[str, str]:
    """Create a JWT refresh token.
    
    Returns:
        Tuple of (token, token_hash) where token_hash should be stored in DB
    """
    settings = get_settings()
    jti = uuid4()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(jti),
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")
    
    # Create hash for storage
    import hashlib
    token_hash = hashlib.sha256(encoded_jwt.encode()).hexdigest()
    
    return encoded_jwt, token_hash


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT token.
    
    Returns:
        Decoded token payload or None if invalid
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.
    
    Returns:
        Tuple of (full_key, prefix, hash) where:
        - full_key: The complete API key (shown once to user)
        - prefix: First 8 characters for identification
        - hash: SHA256 hash for storage
    """
    import secrets
    import hashlib
    
    # Generate random key: si_ prefix + 48 random chars
    random_part = secrets.token_urlsafe(36)
    full_key = f"si_{random_part}"
    
    prefix = full_key[:8]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    return full_key, prefix, key_hash


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    import hashlib
    computed_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return computed_hash == stored_hash


def create_password_reset_token(user_id: UUID) -> str:
    """Create a password reset token (valid for 1 hour)."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=1)
    
    to_encode = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    
    return jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")

def create_email_verification_token(user_id: UUID) -> str:
    """Create a short-lived JWT used to verify a newly registered email."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=48)
    payload = {
        "sub": str(user_id),
        "type": "email_verify",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm="HS256")

