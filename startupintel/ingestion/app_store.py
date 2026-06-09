"""App Store connector for app reviews and version history."""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector


class AppStoreConnector(BaseConnector):
    """Connector for App Store to fetch review velocity and version history."""

    source_name = "app_store"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().app_store_api_key

    async def fetch(self, app_id: str | None = None, app_name: str | None = None) -> dict:
        """Fetch app data from App Store."""
        if not app_id and not app_name:
            raise ValueError("Either app_id or app_name required")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for app if name provided
            if not app_id and app_name:
                app_id = await self._search_app(client, app_name)
                if not app_id:
                    return {"found": False, "source": self.source_name}

            # Get app details
            app_data = await self._get_app_details(client, app_id)

            if not app_data:
                return {"found": False, "source": self.source_name}

            # Get reviews
            reviews = await self._get_reviews(client, app_id)

            return {
                "found": True,
                "source": self.source_name,
                "app_id": app_id,
                "app_name": app_data.get("trackName"),
                "developer": app_data.get("artistName"),
                "current_version": app_data.get("version"),
                "release_date": app_data.get("releaseDate"),
                "current_version_release_date": app_data.get("currentVersionReleaseDate"),
                "average_user_rating": app_data.get("averageUserRating"),
                "user_rating_count": app_data.get("userRatingCount"),
                "price": app_data.get("price"),
                "genres": app_data.get("genres", []),
                "description": app_data.get("description", "")[:500],
                "total_reviews_fetched": len(reviews),
                "reviews": reviews[:50],  # Limit to 50 reviews
            }

    async def _search_app(self, client: httpx.AsyncClient, app_name: str) -> str | None:
        """Search for an app by name and return app ID."""
        try:
            url = "https://itunes.apple.com/search"
            params = {
                "term": app_name,
                "entity": "software",
                "limit": 1,
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                return str(results[0].get("trackId"))
            return None

        except httpx.HTTPError:
            return None

    async def _get_app_details(self, client: httpx.AsyncClient, app_id: str) -> dict:
        """Get detailed app information."""
        try:
            url = f"https://itunes.apple.com/lookup?id={app_id}"

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            return results[0] if results else {}

        except httpx.HTTPError:
            return {}

    async def _get_reviews(self, client: httpx.AsyncClient, app_id: str) -> list[dict]:
        """Fetch app reviews from RSS feed."""

        try:
            # App Store provides RSS feeds for reviews
            url = f"https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortby=mostrecent/json"

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            entries = data.get("feed", {}).get("entry", [])

            reviews = []
            for entry in entries:
                if isinstance(entry, dict):
                    reviews.append({
                        "id": entry.get("id", {}).get("label"),
                        "title": entry.get("title", {}).get("label"),
                        "content": entry.get("content", {}).get("label"),
                        "rating": entry.get("im:rating", {}).get("label"),
                        "author": entry.get("author", {}).get("name", {}).get("label"),
                        "date": entry.get("updated", {}).get("label"),
                    })

            return reviews

        except Exception:
            return []

    async def get_review_velocity(self, app_id: str, days: int = 30) -> dict:
        """Calculate review velocity over time."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            reviews = await self._get_reviews(client, app_id)

            if not reviews:
                return {"velocity": 0, "recent_reviews": 0}

            # Count reviews in the specified time period
            cutoff = datetime.utcnow() - timedelta(days=days)
            recent_count = 0

            for review in reviews:
                review_date = review.get("date")
                if review_date:
                    try:
                        dt = datetime.fromisoformat(review_date.replace("Z", "+00:00"))
                        if dt.replace(tzinfo=None) > cutoff:
                            recent_count += 1
                    except (ValueError, TypeError):
                        pass

            return {
                "velocity": round(recent_count / days, 2),
                "recent_reviews": recent_count,
                "total_reviews": len(reviews),
                "period_days": days,
            }

    async def get_version_history(self, app_id: str) -> list[dict]:
        """Get version release history."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            app_data = await self._get_app_details(client, app_id)

            # Note: App Store API doesn't provide full version history
            # This is a simplified implementation
            return [{
                "version": app_data.get("version"),
                "release_date": app_data.get("currentVersionReleaseDate"),
                "release_notes": app_data.get("releaseNotes", "")[:200],
            }] if app_data else []
