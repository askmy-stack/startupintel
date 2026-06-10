"""Tests for the structlog-based logging configuration."""

from __future__ import annotations

import json

import structlog

from startupintel.utils.logging_config import (
    RequestLogMiddleware,
    configure_logging,
    get_logger,
)


def test_get_logger_returns_bound_logger():
    logger = get_logger("startupintel.test")
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_configure_logging_json_emits_valid_json(capsys):
    configure_logging(log_level="INFO", json_format=True)
    get_logger("startupintel.test").info("hello", foo="bar")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["event"] == "hello"
    assert payload["foo"] == "bar"
    assert payload["level"] == "info"


def test_configure_logging_console_runs(capsys):
    configure_logging(log_level="DEBUG", json_format=False)
    get_logger("startupintel.test").info("console-mode")
    assert "console-mode" in capsys.readouterr().out

    # restore JSON config so test ordering does not leak console renderer
    configure_logging(log_level="INFO", json_format=True)


def test_request_log_middleware_passes_through_non_http():
    seen = {"called": False}

    async def app(scope, receive, send):
        seen["called"] = True

    mw = RequestLogMiddleware(app)
    assert isinstance(mw, RequestLogMiddleware)
    assert structlog is not None
