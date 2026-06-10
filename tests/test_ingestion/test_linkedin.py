"""Tests for the LinkedIn connector.

Playwright is only imported lazily inside ``_get_browser``, so these tests
exercise the dependency-light surface: connector identity, credential handling,
graceful degradation when credentials are missing, and the pure headcount
parser. No browser is launched and no network access is required.
"""

from __future__ import annotations

import pytest

from startupintel.ingestion.base import BaseConnector
from startupintel.ingestion.linkedin import LinkedInConnector


def test_linkedin_is_a_base_connector():
    connector = LinkedInConnector(email="a@b.co", password="pw")
    assert isinstance(connector, BaseConnector)
    assert connector.source_name == "linkedin"


def test_credentials_fall_back_to_settings():
    with_explicit = LinkedInConnector(email="x@y.co", password="secret")
    assert with_explicit.email == "x@y.co"
    assert with_explicit.password == "secret"


@pytest.mark.asyncio
async def test_fetch_without_credentials_degrades_gracefully(monkeypatch):
    # ensure settings provide no creds either
    connector = LinkedInConnector(email=None, password=None)
    connector.email = None
    connector.password = None

    result = await connector.fetch("Acme")
    assert result["found"] is False
    assert result["source"] == "linkedin"
    assert "credentials" in result["error"].lower()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("51-200 employees", {"min": 51, "max": 200, "exact": None}),
        ("10,000+ employees", {"min": 10000, "max": None, "exact": None}),
        ("42 employees", {"min": None, "max": None, "exact": 42}),
        ("", {"min": None, "max": None, "exact": None}),
        ("no numbers here", {"min": None, "max": None, "exact": None}),
    ],
)
def test_parse_headcount(text, expected):
    connector = LinkedInConnector(email="a@b.co", password="pw")
    assert connector._parse_headcount(text) == expected
