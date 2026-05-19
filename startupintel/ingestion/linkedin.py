"""LinkedIn connector for headcount and hiring data using Playwright."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser


class LinkedInConnector(BaseConnector):
    """Connector for LinkedIn to fetch headcount and hiring signals."""

    source_name = "linkedin"

    def __init__(self, email: str | None = None, password: str | None = None):
        self.email = email or get_settings().linkedin_email
        self.password = password or get_settings().linkedin_password
        self._browser: Browser | None = None

    async def _get_browser(self):
        """Get or create browser instance."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
        return self._browser

    async def fetch(self, company_name: str) -> dict:
        """Fetch company headcount data from LinkedIn."""
        if not self.email or not self.password:
            return {"found": False, "source": self.source_name, "error": "LinkedIn credentials not configured"}

        browser = await self._get_browser()
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login
            await self._login(page)

            # Search for company
            company_data = await self._get_company_data(page, company_name)

            await context.close()
            return company_data

        except Exception as e:
            await context.close()
            return {"found": False, "source": self.source_name, "error": str(e)}

    async def _login(self, page: Page) -> None:
        """Login to LinkedIn."""
        await page.goto("https://www.linkedin.com/login")
        await page.fill("#username", self.email)
        await page.fill("#password", self.password)
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")

    async def _get_company_data(self, page: Page, company_name: str) -> dict:
        """Get company data from LinkedIn."""
        # Search for company
        search_url = f"https://www.linkedin.com/search/results/companies/?keywords={company_name.replace(' ', '%20')}"
        await page.goto(search_url)
        await page.wait_for_load_state("networkidle")

        # Try to find company link
        try:
            company_link = await page.locator(".search-results-container a[href*='/company/']").first.get_attribute("href")
            if not company_link:
                return {"found": False, "source": self.source_name}

            # Navigate to company page
            await page.goto(f"https://www.linkedin.com{company_link}")
            await page.wait_for_load_state("networkidle")

            # Extract data
            headcount_text = await self._extract_headcount(page)
            hiring_text = await self._extract_hiring_info(page)

            # Parse headcount
            headcount = self._parse_headcount(headcount_text)

            return {
                "found": True,
                "source": self.source_name,
                "company_name": company_name,
                "headcount": headcount,
                "headcount_text": headcount_text,
                "hiring_text": hiring_text,
                "scraped_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {"found": False, "source": self.source_name, "error": str(e)}

    async def _extract_headcount(self, page: Page) -> str:
        """Extract headcount information."""
        try:
            # Look for company size in the about section
            about_link = await page.locator("a[href*='about']").first
            if about_link:
                await about_link.click()
                await page.wait_for_load_state("networkidle")

            # Try to find company size text
            size_selectors = [
                "text=/\\d+.*employees/i",
                "[data-test-id='about-company-size']",
                ".company-size-text",
            ]

            for selector in size_selectors:
                try:
                    element = await page.locator(selector).first
                    text = await element.text_content()
                    if text:
                        return text.strip()
                except:
                    continue

            return ""
        except:
            return ""

    async def _extract_hiring_info(self, page: Page) -> str:
        """Extract hiring information."""
        try:
            # Look for jobs link
            jobs_link = await page.locator("a[href*='jobs']").first
            if jobs_link:
                # Get job count if available
                text = await jobs_link.text_content()
                return text.strip() if text else ""
            return ""
        except:
            return ""

    def _parse_headcount(self, text: str) -> dict:
        """Parse headcount text into structured data."""
        import re

        result = {"min": None, "max": None, "exact": None}

        if not text:
            return result

        # Look for ranges like "51-200 employees"
        range_match = re.search(r'(\d+)[-–]\s*(\d+)', text)
        if range_match:
            result["min"] = int(range_match.group(1))
            result["max"] = int(range_match.group(2))
            return result

        # Look for "10,000+ employees"
        plus_match = re.search(r'(\d{1,3}(?:,\d{3})*)\+', text)
        if plus_match:
            num = int(plus_match.group(1).replace(',', ''))
            result["min"] = num
            return result

        # Look for single number
        single_match = re.search(r'(\d+)', text)
        if single_match:
            result["exact"] = int(single_match.group(1))

        return result

    async def fetch_job_postings(self, company_name: str) -> list[dict]:
        """Fetch job postings for a company."""
        browser = await self._get_browser()
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await self._login(page)

            # Navigate to company jobs
            jobs_url = f"https://www.linkedin.com/jobs/search/?f_C={company_name.replace(' ', '%20')}"
            await page.goto(jobs_url)
            await page.wait_for_load_state("networkidle")

            # Extract job listings
            jobs = []
            job_cards = await page.locator(".jobs-search-results__list-item").all()

            for card in job_cards[:20]:  # Limit to 20 jobs
                try:
                    title = await card.locator(".job-card-list__title").text_content()
                    location = await card.locator(".job-card-container__metadata-item").text_content()
                    jobs.append({
                        "title": title.strip() if title else None,
                        "location": location.strip() if location else None,
                    })
                except:
                    continue

            await context.close()
            return jobs

        except Exception as e:
            await context.close()
            return []

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
