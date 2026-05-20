"""Feature flag management routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from startupintel.api.dependencies.auth import get_current_user, require_admin
from startupintel.api.schemas.auth import UserResponse
from startupintel.utils.feature_flags import (
    FeatureFlag,
    FeatureFlagCondition,
    FeatureFlagManager,
    FeatureFlagOperator,
    FeatureFlagStrategy,
    feature_flags,
)

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@router.get("/")
async def list_flags(
    user: UserResponse = Depends(require_admin),
) -> dict:
    """List all feature flags (admin only)."""
    flags = await feature_flags.list_flags()
    
    return {
        "items": [
            {
                "key": f.key,
                "name": f.name,
                "description": f.description,
                "strategy": f.strategy.value,
                "enabled": f.enabled,
                "percentage": f.percentage,
                "conditions_count": len(f.conditions),
                "has_variants": f.variants is not None,
                "updated_at": f.updated_at.isoformat(),
                "expires_at": f.expires_at.isoformat() if f.expires_at else None,
            }
            for f in flags
        ],
        "total": len(flags),
    }


@router.get("/{flag_key}")
async def get_flag(
    flag_key: str,
    user: UserResponse = Depends(require_admin),
) -> dict:
    """Get feature flag details (admin only)."""
    from startupintel.db.redis import get_redis
    import json
    
    redis = get_redis()
    data = await redis.get(f"ff:{flag_key}")
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )
    
    return json.loads(data)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_key: str,
    name: str,
    description: str = "",
    strategy: FeatureFlagStrategy = FeatureFlagStrategy.ALWAYS_OFF,
    enabled: bool = True,
    percentage: int = 0,
    user: UserResponse = Depends(require_admin),
) -> dict:
    """Create a new feature flag (admin only)."""
    flag = FeatureFlag(
        key=flag_key,
        name=name,
        description=description,
        strategy=strategy,
        enabled=enabled,
        percentage=percentage,
    )
    
    created = await feature_flags.create_flag(flag)
    
    return {
        "key": created.key,
        "name": created.name,
        "strategy": created.strategy.value,
        "enabled": created.enabled,
        "created_at": created.created_at.isoformat(),
    }


@router.put("/{flag_key}")
async def update_flag(
    flag_key: str,
    name: str | None = None,
    description: str | None = None,
    enabled: bool | None = None,
    percentage: int | None = None,
    user: UserResponse = Depends(require_admin),
) -> dict:
    """Update feature flag (admin only)."""
    from startupintel.db.redis import get_redis
    import json
    
    redis = get_redis()
    data = await redis.get(f"ff:{flag_key}")
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )
    
    flag_dict = json.loads(data)
    
    if name is not None:
        flag_dict["name"] = name
    if description is not None:
        flag_dict["description"] = description
    if enabled is not None:
        flag_dict["enabled"] = enabled
    if percentage is not None:
        flag_dict["percentage"] = percentage
    
    flag_dict["updated_at"] = datetime.now(UTC).isoformat()
    
    await redis.setex(
        f"ff:{flag_key}",
        timedelta(seconds=300),
        json.dumps(flag_dict, default=str),
    )
    
    return {"message": "Feature flag updated", "key": flag_key}


@router.delete("/{flag_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    flag_key: str,
    user: UserResponse = Depends(require_admin),
) -> None:
    """Delete feature flag (admin only)."""
    success = await feature_flags.delete_flag(flag_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete feature flag",
        )


@router.get("/check/{flag_key}")
async def check_flag(
    flag_key: str,
    user: UserResponse = Depends(get_current_user),
) -> dict:
    """Check if feature flag is enabled for current user."""
    context = {
        "user_id": str(user.id),
        "org_id": str(user.organization_id),
        "user.role": user.role,
    }
    
    is_enabled = await feature_flags.is_enabled(flag_key, context)
    variant = await feature_flags.get_variant(flag_key, context)
    
    return {
        "flag_key": flag_key,
        "enabled": is_enabled,
        "variant": variant,
        "user_id": str(user.id),
    }


@router.post("/{flag_key}/enable")
async def enable_flag(
    flag_key: str,
    user: UserResponse = Depends(require_admin),
) -> dict:
    """Enable a feature flag globally (admin only)."""
    return await update_flag(flag_key, enabled=True, user=user)


@router.post("/{flag_key}/disable")
async def disable_flag(
    flag_key: str,
    user: UserResponse = Depends(require_admin),
) -> dict:
    """Disable a feature flag globally (admin only)."""
    return await update_flag(flag_key, enabled=False, user=user)
