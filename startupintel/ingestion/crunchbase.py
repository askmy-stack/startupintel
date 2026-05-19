"""Crunchbase API connector for funding and company data."""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class CrunchbaseConnector(BaseConnector):
    """Connector for Crunchbase API to fetch funding, exits, and founding data."""

    source_name = "crunchbase"
    base_url = "https://api.crunchbase.com/api/v4"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().crunchbase_api_key
        if not self.api_key:
            raise ValueError("Crunchbase API key required")

    async def fetch(self, domain: str | None = None, company_name: str | None = None) -> dict:
        """Fetch company data from Crunchbase by domain or name."""
        if not domain and not company_name:
            raise ValueError("Either domain or company_name required")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for company
            search_term = domain or company_name
            search_result = await self._search(client, search_term)

            if not search_result or "entities" not in search_result:
                return {"found": False, "source": self.source_name}

            entities = search_result["entities"]
            if not entities:
                return {"found": False, "source": self.source_name}

            # Get detailed data for first match
            entity = entities[0]
            entity_id = entity.get("identifier", {}).get("uuid")
            entity_url = entity.get("identifier", {}).get("permalink")

            # Fetch detailed company data
            details = await self._get_company_details(client, entity_id)

            return {
                "found": True,
                "source": self.source_name,
                "entity_id": entity_id,
                "permalink": entity_url,
                "name": details.get("properties", {}).get("name"),
                "founded_year": details.get("properties", {}).get("founded_on", {}).get("year"),
                "employee_count": details.get("properties", {}).get("num_employees_enum"),
                "total_funding": self._parse_funding(details.get("funding_total", {})),
                "last_funding_date": details.get("properties", {}).get("last_funding_at"),
                "last_funding_type": details.get("properties", {}).get("last_funding_type"),
                "stage": details.get("properties", {}).get("funding_stage"),
                "industry": details.get("properties", {}).get("categories"),
                "location": {
                    "city": details.get("properties", {}).get("location_identifiers", [{}])[0].get("value"),
                    "country": details.get("properties", {}).get("location_identifiers", [{}])[1].get("value"),
                },
                "funding_rounds": self._extract_funding_rounds(details.get("funding_rounds", {}).get("entities", [])),
                "investors": self._extract_investors(details.get("investors", {}).get("entities", [])),
            }

    async def _search(self, client: httpx.AsyncClient, query: str) -> dict:
        """Search for companies on Crunchbase."""
        headers = {"X-cb-user-key": self.api_key}
        params = {
            "query": query,
            "limit": 5,
            "collection_ids": "organization.companies",
        }

        try:
            response = await client.get(
                f"{self.base_url}/searches/organizations",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e), "entities": []}

    async def _get_company_details(self, client: httpx.AsyncClient, entity_id: str) -> dict:
        """Get detailed company information."""
        headers = {"X-cb-user-key": self.api_key}

        try:
            response = await client.get(
                f"{self.base_url}/entities/organizations/{entity_id}",
                headers=headers,
                params={
                    "field_ids": "name,founded_on,num_employees_enum,last_funding_at,last_funding_type,funding_stage,categories,location_identifiers",
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {}

    def _parse_funding(self, funding_data: dict) -> float | None:
        """Parse funding amount from Crunchbase format."""
        if not funding_data:
            return None
        value = funding_data.get("value")
        if value is None:
            return None
        currency = funding_data.get("currency", "USD")
        # Convert to USD if needed (simplified)
        return float(value)

    def _extract_funding_rounds(self, rounds: list[dict]) -> list[dict]:
        """Extract funding round information."""
        return [
            {
                "round_type": r.get("properties", {}).get("funding_type"),
                "announced_on": r.get("properties", {}).get("announced_on"),
                "money_raised": self._parse_funding(r.get("money_raised", {})),
            }
            for r in rounds
        ]

    def _extract_investors(self, investors: list[dict]) -> list[dict]:
        """Extract investor information."""
        return [
            {
                "name": i.get("properties", {}).get("name"),
                "type": i.get("properties", {}).get("investor_type"),
            }
            for i in investors
        ]

    async def fetch_funding_rounds(self, entity_id: str) -> list[dict]:
        """Fetch all funding rounds for a company."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"X-cb-user-key": self.api_key}

            try:
                response = await client.get(
                    f"{self.base_url}/entities/organizations/{entity_id}/funding_rounds",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return self._extract_funding_rounds(data.get("entities", []))
            except httpx.HTTPError:
                return []
