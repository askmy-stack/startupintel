"""Structured JSON logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Whether to output JSON formatted logs
    """
    # Configure structlog processors
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    if json_format:
        # JSON formatting for production
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console formatting for development
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        A configured structlog logger
    """
    return structlog.get_logger(name)


class RequestLogMiddleware:
    """ASGI middleware for request logging."""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("startupintel.request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        from uuid import uuid4
        
        request_id = str(uuid4())
        start_time = time.time()
        
        # Bind request context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope.get("method", "UNKNOWN"),
            path=scope.get("path", "UNKNOWN"),
        )
        
        self.logger.info("request_started")
        
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            self.logger.error("request_failed", error=str(e))
            raise
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self.logger.info("request_completed", duration_ms=duration_ms)
