"""Tests for the HTTP/stdlib ingestion connectors.

These exercise the dependency-light paths: each connector's identity
(``source_name`` + ``BaseConnector`` contract), credential handling, and the
"not found" / graceful-degradation branches. Network calls are mocked, so no
real API access (or optional heavy deps) is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from startupintel.ingestion.app_store import AppStoreConnector
from startupintel.ingestion.base import BaseConnector
from startupintel.ingestion.domain_whois import DomainWHOISConnector
from startupintel.ingestion.github import GitHubConnector
from startupintel.ingestion.job_boards import JobBoardsConnector
from startupintel.ingestion.producthunt import ProductHuntConnector
from startupintel.ingestion.sec_edgar import SECEDGARConnector
from startupintel.ingestion.twitter import TwitterConnector
from startupintel.ingestion.wayback import WaybackConnector


def _build_all() -> list[BaseConnector]:
    return [
        GitHubConnector(),
        SECEDGARConnector(),
        ProductHuntConnector(token="dummy-token"),
        WaybackConnector(),
        JobBoardsConnector(),
        AppStoreConnector(),
        TwitterConnector(bearer_token="dummy-token"),
        DomainWHOISConnector(),
    ]


def test_connectors_are_base_connectors_with_source_names():
    expected = {
        "github",
        "sec_edgar",
        "producthunt",
        "wayback",
        "job_boards",
        "app_store",
        "twitter",
        "domain_whois",
    }
    connectors = _build_all()
    assert {c.source_name for c in connectors} == expected
    assert all(isinstance(c, BaseConnector) for c in connectors)


def test_github_token_sets_auth_header():
    assert "Authorization" not in GitHubConnector().headers
    assert GitHubConnector(token="abc").headers["Authorization"] == "token abc"


def test_twitter_requires_bearer_token():
    with patch("startupintel.ingestion.twitter.get_settings") as mock_settings:
        mock_settings.return_value.twitter_bearer_token = None
        with pytest.raises(ValueError, match="bearer token"):
            TwitterConnector()


@pytest.mark.asyncio
async def test_github_fetch_not_found():
    connector = GitHubConnector(token="t")
    with patch.object(connector, "_get_repo", new=AsyncMock(return_value={})):
        result = await connector.fetch("owner", "missing")
    assert result == {"found": False, "source": "github"}


@pytest.mark.asyncio
async def test_github_fetch_found_aggregates_helpers():
    connector = GitHubConnector(token="t")
    with (
        patch.object(
            connector,
            "_get_repo",
            new=AsyncMock(return_value={"id": 1, "name": "repo", "stargazers_count": 42}),
        ),
        patch.object(connector, "_get_contributors", new=AsyncMock(return_value=[])),
        patch.object(connector, "_get_recent_commits", new=AsyncMock(return_value=[])),
        patch.object(connector, "_get_languages", new=AsyncMock(return_value={})),
    ):
        result = await connector.fetch("owner", "repo")
    assert result["found"] is True
    assert result["source"] == "github"
    assert result["stars"] == 42


@pytest.mark.asyncio
async def test_twitter_fetch_not_found():
    connector = TwitterConnector(bearer_token="t")
    with patch.object(connector, "_get_user", new=AsyncMock(return_value={"error": "x"})):
        result = await connector.fetch("nobody")
    assert result == {"found": False, "source": "twitter"}


@pytest.mark.asyncio
async def test_domain_whois_degrades_without_library():
    """When the optional ``whois`` package is absent, fetch reports it cleanly."""
    with patch("startupintel.ingestion.domain_whois.WHOIS_AVAILABLE", False):
        result = await DomainWHOISConnector().fetch("example.com")
    assert result["found"] is False
    assert result["source"] == "domain_whois"
    assert "whois not installed" in result["error"]
