"""Feature flag system for gradual rollouts and A/B testing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable
from uuid import UUID

from startupintel.db.redis import get_redis


class FeatureFlagOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class FeatureFlagStrategy(str, Enum):
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PERCENTAGE = "percentage"
    USER_ID = "user_id"
    ORG_ID = "org_id"
    ATTRIBUTE = "attribute"


@dataclass
class FeatureFlagCondition:
    """Condition for targeting a feature flag."""
    attribute: str  # e.g., "user.role", "org.plan", "user.email"
    operator: FeatureFlagOperator
    value: Any


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    key: str
    name: str
    description: str
    strategy: FeatureFlagStrategy
    enabled: bool = True
    percentage: int = 0  # 0-100 for percentage rollout
    conditions: list[FeatureFlagCondition] = field(default_factory=list)
    variants: dict[str, Any] | None = None  # For A/B testing
    default_value: Any = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


class FeatureFlagManager:
    """Manager for feature flags with Redis caching."""
    
    CACHE_PREFIX = "ff:"
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self):
        self._local_cache: dict[str, FeatureFlag] = {}
        self._last_refresh: datetime | None = None
    
    def _cache_key(self, flag_key: str) -> str:
        return f"{self.CACHE_PREFIX}{flag_key}"
    
    async def _get_from_redis(self, flag_key: str) -> FeatureFlag | None:
        """Get flag from Redis cache."""
        try:
            redis = get_redis()
            data = await redis.get(self._cache_key(flag_key))
            if data:
                flag_dict = json.loads(data)
                return self._dict_to_flag(flag_dict)
        except Exception:
            pass
        return None
    
    async def _set_in_redis(self, flag: FeatureFlag) -> None:
        """Store flag in Redis cache."""
        try:
            redis = get_redis()
            flag_dict = self._flag_to_dict(flag)
            await redis.setex(
                self._cache_key(flag.key),
                timedelta(seconds=self.CACHE_TTL),
                json.dumps(flag_dict, default=str),
            )
        except Exception:
            pass
    
    def _flag_to_dict(self, flag: FeatureFlag) -> dict:
        """Convert flag to dictionary."""
        return {
            "key": flag.key,
            "name": flag.name,
            "description": flag.description,
            "strategy": flag.strategy.value,
            "enabled": flag.enabled,
            "percentage": flag.percentage,
            "conditions": [
                {
                    "attribute": c.attribute,
                    "operator": c.operator.value,
                    "value": c.value,
                }
                for c in flag.conditions
            ],
            "variants": flag.variants,
            "default_value": flag.default_value,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "expires_at": flag.expires_at.isoformat() if flag.expires_at else None,
        }
    
    def _dict_to_flag(self, data: dict) -> FeatureFlag:
        """Convert dictionary to flag."""
        return FeatureFlag(
            key=data["key"],
            name=data["name"],
            description=data["description"],
            strategy=FeatureFlagStrategy(data["strategy"]),
            enabled=data["enabled"],
            percentage=data["percentage"],
            conditions=[
                FeatureFlagCondition(
                    attribute=c["attribute"],
                    operator=FeatureFlagOperator(c["operator"]),
                    value=c["value"],
                )
                for c in data.get("conditions", [])
            ],
            variants=data.get("variants"),
            default_value=data.get("default_value", False),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )
    
    def _evaluate_condition(
        self,
        condition: FeatureFlagCondition,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a single condition against context."""
        # Get attribute value from context (supports nested paths like "user.role")
        value = context
        for key in condition.attribute.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        
        if value is None:
            return False
        
        # Evaluate based on operator
        op = condition.operator
        
        if op == FeatureFlagOperator.EQUALS:
            return value == condition.value
        elif op == FeatureFlagOperator.NOT_EQUALS:
            return value != condition.value
        elif op == FeatureFlagOperator.IN:
            return value in condition.value
        elif op == FeatureFlagOperator.NOT_IN:
            return value not in condition.value
        elif op == FeatureFlagOperator.GREATER_THAN:
            return value > condition.value
        elif op == FeatureFlagOperator.LESS_THAN:
            return value < condition.value
        elif op == FeatureFlagOperator.CONTAINS:
            return condition.value in str(value)
        elif op == FeatureFlagOperator.STARTS_WITH:
            return str(value).startswith(str(condition.value))
        elif op == FeatureFlagOperator.ENDS_WITH:
            return str(value).endswith(str(condition.value))
        
        return False
    
    def _evaluate_conditions(
        self,
        conditions: list[FeatureFlagCondition],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate all conditions (AND logic)."""
        if not conditions:
            return True
        return all(self._evaluate_condition(c, context) for c in conditions)
    
    def _hash_for_percentage(self, identifier: str, salt: str = "") -> int:
        """Hash identifier to get a percentage value (0-100)."""
        hash_input = f"{salt}:{identifier}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        return int(hash_value[:8], 16) % 100
    
    async def is_enabled(
        self,
        flag_key: str,
        context: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        """Check if feature flag is enabled for given context."""
        flag = await self._get_from_redis(flag_key)
        
        if not flag:
            return default
        
        # Check if expired
        if flag.expires_at and flag.expires_at < datetime.now(UTC):
            return default
        
        # Check if globally disabled
        if not flag.enabled:
            return False
        
        ctx = context or {}
        
        # Evaluate based on strategy
        if flag.strategy == FeatureFlagStrategy.ALWAYS_ON:
            return self._evaluate_conditions(flag.conditions, ctx)
        
        if flag.strategy == FeatureFlagStrategy.ALWAYS_OFF:
            return False
        
        if flag.strategy == FeatureFlagStrategy.PERCENTAGE:
            user_id = ctx.get("user_id")
            if not user_id:
                return flag.percentage > 50  # Default to enabled if no user
            user_hash = self._hash_for_percentage(str(user_id), flag_key)
            return user_hash < flag.percentage and self._evaluate_conditions(flag.conditions, ctx)
        
        if flag.strategy == FeatureFlagStrategy.USER_ID:
            user_id = ctx.get("user_id")
            if not user_id:
                return False
            return self._hash_for_percentage(str(user_id), flag_key) < flag.percentage
        
        if flag.strategy == FeatureFlagStrategy.ORG_ID:
            org_id = ctx.get("org_id")
            if not org_id:
                return False
            return self._hash_for_percentage(str(org_id), flag_key) < flag.percentage
        
        if flag.strategy == FeatureFlagStrategy.ATTRIBUTE:
            return self._evaluate_conditions(flag.conditions, ctx)
        
        return default
    
    async def get_variant(
        self,
        flag_key: str,
        context: dict[str, Any] | None = None,
        default_variant: str = "control",
    ) -> str:
        """Get A/B test variant for user."""
        flag = await self._get_from_redis(flag_key)
        
        if not flag or not flag.variants:
            return default_variant
        
        ctx = context or {}
        user_id = ctx.get("user_id")
        
        if not user_id:
            return default_variant
        
        # Use hash to deterministically assign variant
        variants = list(flag.variants.keys())
        user_hash = self._hash_for_percentage(str(user_id), f"{flag_key}:variant")
        variant_index = user_hash % len(variants)
        
        return variants[variant_index]
    
    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create or update a feature flag."""
        flag.updated_at = datetime.now(UTC)
        await self._set_in_redis(flag)
        return flag
    
    async def delete_flag(self, flag_key: str) -> bool:
        """Delete a feature flag."""
        try:
            redis = get_redis()
            await redis.delete(self._cache_key(flag_key))
            return True
        except Exception:
            return False
    
    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        try:
            redis = get_redis()
            keys = await redis.keys(f"{self.CACHE_PREFIX}*")
            flags = []
            for key in keys:
                data = await redis.get(key)
                if data:
                    flag_dict = json.loads(data)
                    flags.append(self._dict_to_flag(flag_dict))
            return flags
        except Exception:
            return []


# Global feature flag manager
feature_flags = FeatureFlagManager()


# Decorator for feature-gated routes
def feature_required(flag_key: str, fallback: Callable | None = None):
    """Decorator to require a feature flag for a route."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Get context from kwargs or args
            context = kwargs.get("context", {})
            
            is_enabled = await feature_flags.is_enabled(flag_key, context)
            
            if not is_enabled:
                if fallback:
                    return await fallback(*args, **kwargs)
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{flag_key}' is not enabled",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Helper functions for common checks
async def is_feature_enabled(flag_key: str, user_id: UUID | None = None, org_id: UUID | None = None) -> bool:
    """Quick check if feature is enabled for user/org."""
    context = {}
    if user_id:
        context["user_id"] = str(user_id)
    if org_id:
        context["org_id"] = str(org_id)
    
    return await feature_flags.is_enabled(flag_key, context)
