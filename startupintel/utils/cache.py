"""Redis-based response caching utilities."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from fastapi import Request, Response
from startupintel.db.redis import get_redis

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CacheManager:
    """Manager for Redis-based caching."""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl  # seconds
    
    def _generate_cache_key(self, prefix: str, request: Request, params: dict | None = None) -> str:
        """Generate a cache key from request."""
        key_parts = [prefix, request.url.path]
        
        # Include query parameters
        if request.query_params:
            query_str = str(sorted(request.query_params.items()))
            key_parts.append(query_str)
        
        # Include custom params
        if params:
            params_str = str(sorted(params.items()))
            key_parts.append(params_str)
        
        # Create hash
        key = ":".join(key_parts)
        return hashlib.sha256(key.encode()).hexdigest()[:32]
    
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            redis = get_redis()
            data = await redis.get(f"cache:{key}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache."""
        try:
            redis = get_redis()
            ttl = ttl or self.default_ttl
            await redis.setex(
                f"cache:{key}",
                timedelta(seconds=ttl),
                json.dumps(value, default=str),
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def delete(self, pattern: str) -> None:
        """Delete cache entries by pattern."""
        try:
            redis = get_redis()
            keys = await redis.keys(f"cache:{pattern}*")
            if keys:
                await redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
    
    async def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all cache entries with prefix."""
        await self.delete(f"{prefix}:*")


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    prefix: str,
    ttl: int = 300,
    key_builder: Callable[[Request], str] | None = None,
):
    """Decorator for caching endpoint responses.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function
        
    Example:
        @router.get("/startups")
        @cached("startups", ttl=60)
        async def list_startups(request: Request):
            return {"items": [...]}
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Find request in args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for arg in kwargs.values():
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # No request found, skip caching
                return await func(*args, **kwargs)
            
            # Generate cache key
            if key_builder:
                cache_key = key_builder(request)
            else:
                cache_key = cache_manager._generate_cache_key(prefix, request)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cast(T, cached_value)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")
            
            return result
        
        # Attach cache invalidation helper
        wrapper.cache_invalidate = lambda: cache_manager.invalidate_prefix(prefix)  # type: ignore
        
        return wrapper
    return decorator


async def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate cache entries matching pattern.
    
    Args:
        pattern: Pattern to match (e.g., "startups:*")
    """
    await cache_manager.delete(pattern)


class CachedResponse:
    """Helper for caching FastAPI responses."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
    
    async def get_or_compute(
        self,
        key: str,
        compute: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Get from cache or compute and store."""
        cached_value = await cache_manager.get(key)
        if cached_value is not None:
            return cached_value
        
        result = await compute(*args, **kwargs)
        await cache_manager.set(key, result, self.ttl)
        return result
