"""Tests for Crunchbase connector."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from startupintel.ingestion.crunchbase import CrunchbaseConnector


@pytest.fixture
def crunchbase_connector():
    """Create Crunchbase connector for testing."""
    return CrunchbaseConnector(api_key="test-key")


@pytest.mark.asyncio
async def test_crunchbase_connector_init(crunchbase_connector):
    """Test Crunchbase connector initialization."""
    assert crunchbase_connector.api_key == "test-key"
    assert crunchbase_connector.base_url == "https://api.crunchbase.com/api/v4"
    assert crunchbase_connector.source_name == "crunchbase"


@pytest.mark.asyncio
async def test_fetch_company_not_found(crunchbase_connector):
    """Test fetching non-existent company."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = await crunchbase_connector.fetch("nonexistent")
        assert result["found"] is False


@pytest.mark.asyncio
async def test_fetch_funding_data_empty(crunchbase_connector):
    """Test fetching funding data with empty response."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entities": []}
        mock_get.return_value = mock_response

        result = await crunchbase_connector.fetch_funding_data("test-company")
        assert result["found"] is False
