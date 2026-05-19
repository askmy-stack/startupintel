"""Data ingestion connectors for StartupIntel."""

from startupintel.ingestion.base import BaseConnector
from startupintel.ingestion.crunchbase import CrunchbaseConnector
from startupintel.ingestion.github import GitHubConnector
from startupintel.ingestion.linkedin import LinkedInConnector
from startupintel.ingestion.twitter import TwitterConnector
from startupintel.ingestion.producthunt import ProductHuntConnector
from startupintel.ingestion.sec_edgar import SECEDGARConnector
from startupintel.ingestion.wayback import WaybackConnector
from startupintel.ingestion.domain_whois import DomainWHOISConnector
from startupintel.ingestion.app_store import AppStoreConnector
from startupintel.ingestion.job_boards import JobBoardsConnector

__all__ = [
    "BaseConnector",
    "CrunchbaseConnector",
    "GitHubConnector",
    "LinkedInConnector",
    "TwitterConnector",
    "ProductHuntConnector",
    "SECEDGARConnector",
    "WaybackConnector",
    "DomainWHOISConnector",
    "AppStoreConnector",
    "JobBoardsConnector",
]
