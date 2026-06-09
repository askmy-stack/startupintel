"""Tests for base ingestion connector."""

from __future__ import annotations

import pytest

from startupintel.ingestion.base import BaseConnector


class TestConnector(BaseConnector):
    """Test implementation of BaseConnector."""

    source_name = "test"

    async def fetch(self, identifier: str) -> dict:
        return {"source": self.source_name, "id": identifier, "found": True}


@pytest.mark.asyncio
async def test_base_connector():
    """Test base connector implementation."""
    connector = TestConnector()

    result = await connector.fetch("test-id")

    assert result["source"] == "test"
    assert result["id"] == "test-id"
    assert result["found"] is True


def test_connector_source_name():
    """Test connector source name."""
    connector = TestConnector()
    assert connector.source_name == "test"
