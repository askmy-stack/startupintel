"""Data ingestion connectors for StartupIntel."""

from startupintel.ingestion.base import BaseConnector
from startupintel.ingestion.crunchbase import CrunchbaseConnector

__all__ = [
    "BaseConnector",
    "CrunchbaseConnector",
]
