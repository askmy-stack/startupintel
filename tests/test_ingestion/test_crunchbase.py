"""Tests for Crunchbase connector."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from startupintel.ingestion.crunchbase import CrunchbaseConnector


@pytest.fixture
def crunchbase_connector():
    """Create Crunchbase connector for testing."""
    return CrunchbaseConnector(api_key="test-key")


def test_crunchbase_connector_init(crunchbase_connector):
    """Connector exposes its identity and is configured with the API key."""
    assert crunchbase_connector.api_key == "test-key"
    assert crunchbase_connector.base_url == "https://api.crunchbase.com/api/v4"
    assert crunchbase_connector.source_name == "crunchbase"


def test_init_requires_api_key():
    """Missing API key (no override, no settings) raises."""
    with patch(
        "startupintel.ingestion.crunchbase.get_settings"
    ) as mock_settings:
        mock_settings.return_value.crunchbase_api_key = None
        with pytest.raises(ValueError, match="Crunchbase API key required"):
            CrunchbaseConnector()


@pytest.mark.asyncio
async def test_fetch_requires_identifier(crunchbase_connector):
    """fetch with neither domain nor company_name raises."""
    with pytest.raises(ValueError, match="domain or company_name required"):
        await crunchbase_connector.fetch()


@pytest.mark.asyncio
async def test_fetch_company_not_found(crunchbase_connector):
    """An empty search result yields found=False."""
    with patch.object(
        crunchbase_connector, "_search", new=AsyncMock(return_value={"entities": []})
    ):
        result = await crunchbase_connector.fetch(company_name="nonexistent")

    assert result["found"] is False
    assert result["source"] == "crunchbase"


@pytest.mark.asyncio
async def test_fetch_company_found(crunchbase_connector):
    """A matching search result is enriched with company details."""
    search_payload = {
        "entities": [
            {"identifier": {"uuid": "abc", "permalink": "acme"}},
        ]
    }
    details_payload = {
        "properties": {
            "name": "Acme",
            "founded_on": {"year": 2015},
            "num_employees_enum": "c_00051_00100",
            "location_identifiers": [{"value": "SF"}, {"value": "US"}],
        },
        "funding_total": {"value": 1000000},
    }
    with patch.object(
        crunchbase_connector, "_search", new=AsyncMock(return_value=search_payload)
    ), patch.object(
        crunchbase_connector,
        "_get_company_details",
        new=AsyncMock(return_value=details_payload),
    ):
        result = await crunchbase_connector.fetch(domain="acme.com")

    assert result["found"] is True
    assert result["entity_id"] == "abc"
    assert result["name"] == "Acme"
    assert result["founded_year"] == 2015
    assert result["total_funding"] == 1000000.0
    assert result["location"] == {"city": "SF", "country": "US"}


def test_parse_funding(crunchbase_connector):
    """Funding parsing handles empty, missing, and present values."""
    assert crunchbase_connector._parse_funding({}) is None
    assert crunchbase_connector._parse_funding({"value": None}) is None
    assert crunchbase_connector._parse_funding({"value": 500}) == 500.0


def test_extract_investors(crunchbase_connector):
    """Investor extraction maps name and type."""
    investors = [
        {"properties": {"name": "VC One", "investor_type": "vc"}},
    ]
    assert crunchbase_connector._extract_investors(investors) == [
        {"name": "VC One", "type": "vc"},
    ]
