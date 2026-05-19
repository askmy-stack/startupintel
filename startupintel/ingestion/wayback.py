"""Wayback Machine connector for historical website snapshots."""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta

from startupintel.config import get_settings
from startupintel.ingestion.base import BaseConnector

try:
    from waybackpy import WaybackMachineCDXServerAPI
    WAYBACKPY_AVAILABLE = True
except ImportError:
    WAYBACKPY_AVAILABLE = False
    WaybackMachineCDXServerAPI = None


class WaybackConnector(BaseConnector):
    """Connector for Wayback Machine to fetch historical website snapshots."""

    source_name = "wayback"

    def __init__(self, user_agent: str = "StartupIntel Bot"):
        self.user_agent = user_agent

    async def fetch(self, url: str, from_date: str | None = None, to_date: str | None = None) -> dict:
        """Fetch historical snapshots for a URL."""
        if not WAYBACKPY_AVAILABLE:
            return {"found": False, "source": self.source_name, "error": "waybackpy not installed"}

        try:
            # Use waybackpy for CDX API access
            cdx_api = WaybackMachineCDXServerAPI(url, self.user_agent)

            # Get snapshots
            snapshots = list(cdx_api.snapshots())

            if not snapshots:
                return {"found": False, "source": self.source_name, "url": url}

            # Filter by date if specified
            if from_date or to_date:
                filtered = []
                for snap in snapshots:
                    snap_date = snap.archive_url.split('/')[4]
                    if from_date and snap_date < from_date.replace('-', ''):
                        continue
                    if to_date and snap_date > to_date.replace('-', ''):
                        continue
                    filtered.append(snap)
                snapshots = filtered

            # Get oldest and newest
            oldest = min(snapshots, key=lambda s: s.timestamp)
            newest = max(snapshots, key=lambda s: s.timestamp)

            # Calculate change frequency
            date_range = self._parse_wayback_date(newest.timestamp) - self._parse_wayback_date(oldest.timestamp)
            days_span = date_range.days if date_range.days > 0 else 1

            return {
                "found": True,
                "source": self.source_name,
                "url": url,
                "total_snapshots": len(snapshots),
                "first_seen": oldest.timestamp,
                "latest_snapshot": newest.timestamp,
                "oldest_archive_url": oldest.archive_url,
                "newest_archive_url": newest.archive_url,
                "snapshot_frequency_per_year": round(len(snapshots) / (days_span / 365), 2),
                "snapshots": [
                    {
                        "timestamp": s.timestamp,
                        "archive_url": s.archive_url,
                    }
                    for s in snapshots[:100]  # Limit to 100 for performance
                ],
            }

        except Exception as e:
            return {"found": False, "source": self.source_name, "url": url, "error": str(e)}

    def _parse_wayback_date(self, timestamp: str) -> datetime:
        """Parse Wayback Machine timestamp format."""
        return datetime.strptime(timestamp, "%Y%m%d%H%M%S")

    async def get_snapshot_content(self, url: str, timestamp: str | None = None) -> str | None:
        """Get the actual HTML content of a snapshot."""
        try:
            cdx_api = WaybackMachineCDXServerAPI(url, self.user_agent)

            if timestamp:
                # Get specific snapshot
                snapshot_url = f"https://web.archive.org/web/{timestamp}/{url}"
            else:
                # Get newest
                snapshots = list(cdx_api.snapshots())
                if not snapshots:
                    return None
                newest = max(snapshots, key=lambda s: s.timestamp)
                snapshot_url = newest.archive_url

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(snapshot_url)
                response.raise_for_status()
                return response.text

        except Exception:
            return None

    async def detect_pivot_signals(self, url: str, months: int = 12) -> dict:
        """Detect potential pivot signals from website changes."""
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=30 * months)

        snapshots = await self.fetch(
            url,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
        )

        if not snapshots.get("found"):
            return {"detected": False, "signals": []}

        # Analyze snapshot metadata for pivot indicators
        snap_list = snapshots.get("snapshots", [])

        # Group by month
        monthly_counts = {}
        for snap in snap_list:
            month_key = snap["timestamp"][:6]  # YYYYMM
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

        # Detect unusual patterns
        signals = []
        counts = list(monthly_counts.values())
        if len(counts) >= 3:
            avg = sum(counts) / len(counts)
            for month, count in monthly_counts.items():
                if count > avg * 3:  # Unusually high activity
                    signals.append({
                        "month": month,
                        "type": "high_activity",
                        "snapshot_count": count,
                        "possible_reason": "Potential rebranding or major site update",
                    })

        return {
            "detected": len(signals) > 0,
            "signals": signals,
            "monthly_snapshot_counts": monthly_counts,
        }
