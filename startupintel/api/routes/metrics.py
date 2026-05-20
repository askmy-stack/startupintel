"""Prometheus metrics endpoint."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

router = APIRouter(prefix="/metrics", tags=["monitoring"])

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

# Application metrics
ACTIVE_CONNECTIONS = Gauge(
    "active_websocket_connections",
    "Number of active WebSocket connections",
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

# Bot metrics
BOT_RUNS = Counter(
    "bot_runs_total",
    "Total bot analysis runs",
    ["bot_name", "status"],
)

BOT_DURATION = Histogram(
    "bot_run_duration_seconds",
    "Bot analysis duration in seconds",
    ["bot_name"],
    buckets=[1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# Database metrics
DB_CONNECTIONS = Gauge(
    "db_connections_active",
    "Active database connections",
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Rate limiting metrics
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["endpoint"],
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service_name"],
)


@router.get("")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


class MetricsMiddleware:
    """ASGI middleware for collecting Prometheus metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "UNKNOWN")
        
        # Normalize path for metrics (remove IDs)
        endpoint = self._normalize_path(path)
        
        # Track in-progress requests
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.time()
        
        # Capture status code
        status_code = "200"
        
        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 200))
            await send(message)
        
        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
            
            REQUEST_IN_PROGRESS.labels(
                method=method,
                endpoint=endpoint,
            ).dec()
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace IDs with placeholders)."""
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE,
        )
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+(/|$)', '/{id}/', path)
        
        return path


def record_cache_hit(cache_type: str = "redis") -> None:
    """Record a cache hit."""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "redis") -> None:
    """Record a cache miss."""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_bot_run(bot_name: str, duration: float, success: bool = True) -> None:
    """Record a bot analysis run."""
    status = "success" if success else "error"
    BOT_RUNS.labels(bot_name=bot_name, status=status).inc()
    BOT_DURATION.labels(bot_name=bot_name).observe(duration)


def record_rate_limit_hit(endpoint: str) -> None:
    """Record a rate limit hit."""
    RATE_LIMIT_HITS.labels(endpoint=endpoint).inc()


def update_circuit_breaker_state(service_name: str, state: str) -> None:
    """Update circuit breaker state metric."""
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
    CIRCUIT_BREAKER_STATE.labels(service_name=service_name).set(state_value)
