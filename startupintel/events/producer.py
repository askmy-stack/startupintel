"""Kafka and in-memory event producers for StartupIntel."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


@dataclass
class InMemoryEventProducer:
    """Test-friendly producer used until Kafka wiring is enabled."""

    events: list[tuple[str, dict]] = field(default_factory=list)

    async def emit(self, topic: str, payload: dict) -> None:
        """Emit event to in-memory storage."""
        self.events.append((topic, payload))
        logger.info(f"[InMemory] Event emitted: {topic}")

    async def start(self) -> None:
        """No-op for in-memory producer."""
        pass

    async def stop(self) -> None:
        """No-op for in-memory producer."""
        pass


class KafkaEventProducer:
    """Production Kafka producer for event streaming."""

    def __init__(self, bootstrap_servers: str, client_id: str = "startupintel-producer"):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialize and start the Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                compression_type="gzip",
                max_batch_size=16384,
                linger_ms=10,
            )
            await self._producer.start()
            logger.info(f"Kafka producer started: {self.client_id}")
        except ImportError:
            logger.error("aiokafka not installed. Install with: pip install aiokafka")
            raise
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def emit(self, topic: str, payload: dict, key: str | None = None) -> None:
        """Emit event to Kafka topic."""
        if not self._producer:
            raise RuntimeError("Producer not started. Call start() first.")

        try:
            await self._producer.send(topic, payload, key=key)
            logger.info(f"[Kafka] Event emitted: {topic}")
        except Exception as e:
            logger.error(f"Failed to emit event to {topic}: {e}")
            raise


# Global producer instance (set during app startup)
_event_producer: InMemoryEventProducer | KafkaEventProducer | None = None


def get_event_producer() -> InMemoryEventProducer | KafkaEventProducer:
    """Get the current event producer."""
    if _event_producer is None:
        # Default to in-memory for safety
        return InMemoryEventProducer()
    return _event_producer


def set_event_producer(producer: InMemoryEventProducer | KafkaEventProducer) -> None:
    """Set the global event producer."""
    global _event_producer
    _event_producer = producer

