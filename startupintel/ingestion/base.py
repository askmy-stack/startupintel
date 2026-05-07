from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    source_name: str

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> dict:
        """Fetch raw source data and return a normalized dictionary."""

