"""SEC EDGAR connector for term sheets and filings."""

from __future__ import annotations

import httpx

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class SECEDGARConnector(BaseConnector):
    """Connector for SEC EDGAR to fetch term sheets, S-1 filings, and other documents."""

    source_name = "sec_edgar"
    base_url = "https://www.sec.gov/Archives/edgar"

    def __init__(self, user_agent: str | None = None):
        self.user_agent = user_agent or get_settings().sec_edgar_user_agent
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    async def fetch(self, cik: str | None = None, ticker: str | None = None) -> dict:
        """Fetch company filings from EDGAR."""
        if not cik and not ticker:
            raise ValueError("Either CIK or ticker required")

        # Convert ticker to CIK if needed
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {"found": False, "source": self.source_name}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get company submissions
            submissions = await self._get_submissions(client, cik)

            if not submissions:
                return {"found": False, "source": self.source_name}

            # Extract recent filings
            recent_filings = self._extract_recent_filings(submissions)

            # Get company info
            company_info = submissions.get("name", ""), submissions.get("sic", ""), submissions.get("sicDescription", "")

            return {
                "found": True,
                "source": self.source_name,
                "cik": cik,
                "company_name": company_info[0],
                "sic_code": company_info[1],
                "sic_description": company_info[2],
                "recent_filings": recent_filings,
                "total_filings": len(recent_filings),
            }

    async def _ticker_to_cik(self, ticker: str) -> str | None:
        """Convert ticker symbol to CIK."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Use SEC company tickers JSON
                response = await client.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                for item in data.values():
                    if item.get("ticker", "").upper() == ticker.upper():
                        return str(item.get("cik_str")).zfill(10)

                return None
            except httpx.HTTPError:
                return None

    async def _get_submissions(self, client: httpx.AsyncClient, cik: str) -> dict:
        """Get company submissions from EDGAR."""
        cik_padded = cik.zfill(10)

        try:
            response = await client.get(
                f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {}

    def _extract_recent_filings(self, submissions: dict) -> list[dict]:
        """Extract recent filing information."""
        recent = submissions.get("filings", {}).get("recent", {})

        form_types = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_documents = recent.get("primaryDocument", [])

        filings = []
        for i in range(min(len(form_types), 50)):  # Last 50 filings
            filings.append({
                "form_type": form_types[i] if i < len(form_types) else None,
                "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                "accession_number": accession_numbers[i] if i < len(accession_numbers) else None,
                "primary_document": primary_documents[i] if i < len(primary_documents) else None,
            })

        return filings

    async def get_filing_content(self, cik: str, accession_number: str, primary_document: str) -> str | None:
        """Get the content of a specific filing."""
        cik_padded = cik.zfill(10)
        acc_no_clean = accession_number.replace("-", "")

        url = f"{self.base_url}/{cik_padded}/{acc_no_clean}/{primary_document}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError:
                return None

    async def search_form_type(self, cik: str, form_type: str, limit: int = 10) -> list[dict]:
        """Search for specific form types (e.g., 'S-1', '10-K', '8-K')."""
        data = await self.fetch(cik=cik)

        if not data.get("found"):
            return []

        filings = data.get("recent_filings", [])
        matching = [f for f in filings if f.get("form_type") == form_type]

        return matching[:limit]

    async def get_term_sheet_signals(self, cik: str) -> dict:
        """Extract term sheet related signals from SEC filings."""
        # Look for recent S-1, S-3, and 8-K filings (often contain term sheet info)
        form_types = ["S-1", "S-3", "8-K", "FWP"]

        signals = {
            "has_recent_s1": False,
            "has_recent_s3": False,
            "recent_8k_count": 0,
            "filing_velocity": 0,
            "last_filing_date": None,
        }

        for form in form_types:
            filings = await self.search_form_type(cik, form, limit=5)

            if form == "S-1" and filings:
                signals["has_recent_s1"] = True
            elif form == "S-3" and filings:
                signals["has_recent_s3"] = True
            elif form == "8-K":
                signals["recent_8k_count"] = len(filings)

        return signals
