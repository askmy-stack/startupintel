"""Domain WHOIS connector for domain expiry checking."""

from __future__ import annotations

from datetime import datetime

from startupintel.ingestion.base import BaseConnector

try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False
    whois = None


class DomainWHOISConnector(BaseConnector):
    """Connector for WHOIS data to check domain expiry and registration info."""

    source_name = "domain_whois"

    async def fetch(self, domain: str) -> dict:
        """Fetch WHOIS data for a domain."""
        if not WHOIS_AVAILABLE:
            return {"found": False, "source": self.source_name, "domain": domain, "error": "whois not installed"}

        try:
            w = whois.whois(domain)

            # Extract expiry date
            expiry = w.expiration_date
            if isinstance(expiry, list):
                expiry = expiry[0]

            # Calculate days until expiry
            days_until_expiry = None
            if expiry:
                if isinstance(expiry, datetime):
                    days_until_expiry = (expiry - datetime.utcnow()).days
                else:
                    try:
                        expiry_dt = datetime.strptime(str(expiry), "%Y-%m-%d %H:%M:%S")
                        days_until_expiry = (expiry_dt - datetime.utcnow()).days
                    except:
                        pass

            # Extract creation date
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]

            domain_age_days = None
            if creation:
                if isinstance(creation, datetime):
                    domain_age_days = (datetime.utcnow() - creation).days
                else:
                    try:
                        creation_dt = datetime.strptime(str(creation), "%Y-%m-%d %H:%M:%S")
                        domain_age_days = (datetime.utcnow() - creation_dt).days
                    except:
                        pass

            return {
                "found": True,
                "source": self.source_name,
                "domain": domain,
                "registrar": w.registrar,
                "creation_date": str(creation) if creation else None,
                "expiration_date": str(expiry) if expiry else None,
                "days_until_expiry": days_until_expiry,
                "domain_age_days": domain_age_days,
                "domain_age_years": round(domain_age_days / 365, 1) if domain_age_days else None,
                "name_servers": w.name_servers if isinstance(w.name_servers, list) else [w.name_servers] if w.name_servers else [],
                "status": w.status if isinstance(w.status, list) else [w.status] if w.status else [],
                "dnssec": w.dnssec,
            }

        except Exception as e:
            return {
                "found": False,
                "source": self.source_name,
                "domain": domain,
                "error": str(e),
            }

    def is_expiring_soon(self, days_until_expiry: int | None, threshold_days: int = 90) -> bool:
        """Check if domain is expiring soon."""
        if days_until_expiry is None:
            return True  # Unknown = risky
        return days_until_expiry <= threshold_days

    def get_renewal_urgency(self, days_until_expiry: int | None) -> str:
        """Get renewal urgency level."""
        if days_until_expiry is None:
            return "unknown"
        if days_until_expiry <= 7:
            return "critical"
        if days_until_expiry <= 30:
            return "urgent"
        if days_until_expiry <= 90:
            return "warning"
        return "ok"
