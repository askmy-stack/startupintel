"""Database and API retry utilities using tenacity."""

from __future__ import annotations

import logging
from typing import TypeVar, Callable, Any
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
from sqlalchemy.exc import (
    OperationalError,
    TimeoutError as SATimeoutError,
    DisconnectionError,
)
import asyncpg

logger = logging.getLogger(__name__)

T = TypeVar("T")


# Database retry configuration
DB_RETRY_EXCEPTIONS = (
    OperationalError,
    SATimeoutError,
    DisconnectionError,
    asyncpg.PostgresConnectionError,
    asyncpg.TooManyConnectionsError,
    ConnectionError,
    OSError,
)


def db_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exponential_base: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for database operation retries.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exponential_base: Base for exponential backoff
        
    Example:
        @db_retry(max_attempts=3)
        async def fetch_startup(db, startup_id: UUID) -> Startup:
            return await db.get(Startup, startup_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=exponential_base, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(DB_RETRY_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def execute_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    **kwargs: Any,
) -> T:
    """Execute a function with database retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments
        max_attempts: Maximum retry attempts
        **kwargs: Keyword arguments
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception after all retries are exhausted
    """
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2.0, min=1.0, max=10.0),
        retry=retry_if_exception_type(DB_RETRY_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _execute() -> T:
        return await func(*args, **kwargs)
    
    return await _execute()


# Pre-configured retry instances for common scenarios
light_retry = db_retry(max_attempts=2, min_wait=0.5, max_wait=2.0)
medium_retry = db_retry(max_attempts=3, min_wait=1.0, max_wait=10.0)
heavy_retry = db_retry(max_attempts=5, min_wait=2.0, max_wait=30.0)
