"""Circuit breaker pattern implementation for resilient external API calls."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing, reject calls
    HALF_OPEN = auto()   # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: float = 60.0       # Seconds before half-open
    half_open_max_calls: int = 3         # Test calls in half-open
    success_threshold: int = 2           # Successes to close


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    failures: int = 0
    successes: int = 0
    last_failure_time: float | None = None
    consecutive_successes: int = 0


class CircuitBreaker:
    """Circuit breaker for resilient external API calls.
    
    Usage:
        breaker = CircuitBreaker("groq_api", failure_threshold=5)
        
        @breaker
        async def call_groq(prompt: str) -> str:
            return await groq_client.generate(prompt)
    
    Or manual usage:
        async with breaker:
            result = await api_call()
    """
    
    _breakers: dict[str, "CircuitBreaker"] = {}
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        expected_exception: type[Exception] = Exception,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        # Register in global registry
        CircuitBreaker._breakers[name] = self
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            await self._update_state()
            
            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN (limit reached)."
                    )
                self._half_open_calls += 1
        
        # Execute outside lock
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except self.expected_exception as e:
            await self._record_failure()
            raise
    
    async def _update_state(self) -> None:
        """Update circuit state based on time and stats."""
        if self._state == CircuitState.OPEN:
            if self._stats.last_failure_time is None:
                return
            
            elapsed = time.time() - self._stats.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
    
    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self._stats.successes += 1
            self._stats.consecutive_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._stats.consecutive_successes = 0
                    self._stats.failures = 0
    
    async def _record_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self._stats.failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._stats.failures >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit breaker '{self.name}' transitioning to OPEN "
                        f"({self._stats.failures} failures)"
                    )
                    self._state = CircuitState.OPEN
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN (test failed)")
                self._state = CircuitState.OPEN
    
    @classmethod
    def get(cls, name: str) -> "CircuitBreaker | None":
        """Get circuit breaker by name."""
        return cls._breakers.get(name)
    
    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return {
            "name": self.name,
            "state": self._state.name,
            "failures": self._stats.failures,
            "successes": self._stats.successes,
            "consecutive_successes": self._stats.consecutive_successes,
            "last_failure_time": self._stats.last_failure_time,
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Pre-configured circuit breakers for common services
DEFAULT_BREAKERS = {
    "groq": CircuitBreaker(
        "groq",
        CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
    ),
    "twitter": CircuitBreaker(
        "twitter",
        CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0),
    ),
    "linkedin": CircuitBreaker(
        "linkedin",
        CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0),
    ),
    "github": CircuitBreaker(
        "github",
        CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
    ),
}


def circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create circuit breaker by name.
    
    Usage:
        @circuit_breaker("groq")
        async def generate_with_groq(prompt: str) -> str:
            return await groq_client.generate(prompt)
    """
    if name in DEFAULT_BREAKERS:
        return DEFAULT_BREAKERS[name]
    
    # Create new breaker if not exists
    existing = CircuitBreaker.get(name)
    if existing:
        return existing
    
    return CircuitBreaker(name)
