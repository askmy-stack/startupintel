"""Kafka consumers for StartupIntel event processing."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    async def handle(self, topic: str, payload: dict) -> None:
        """Handle an incoming event."""
        pass


class KafkaEventConsumer:
    """Kafka consumer for processing events."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        handler: EventHandler | Callable[[str, dict], None],
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.handler = handler
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the Kafka consumer."""
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                max_poll_records=100,
            )
            await self._consumer.start()
            self._running = True
            logger.info(f"Kafka consumer started: {self.group_id} on topics {self.topics}")

            # Start consuming
            await self._consume()

        except ImportError:
            logger.error("aiokafka not installed. Install with: pip install aiokafka")
            raise
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def _consume(self) -> None:
        """Consume messages from Kafka."""
        if not self._consumer:
            raise RuntimeError("Consumer not started")

        try:
            async for msg in self._consumer:
                if not self._running:
                    break

                try:
                    topic = msg.topic
                    payload = msg.value
                    key = msg.key

                    logger.info(f"[Kafka] Received: {topic} (key={key})")

                    # Handle the event
                    if isinstance(self.handler, EventHandler):
                        await self.handler.handle(topic, payload)
                    else:
                        await self.handler(topic, payload)

                except Exception as e:
                    logger.error(f"Error processing message from {msg.topic}: {e}")
                    # Continue processing other messages

        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")


class StartupIntelEventHandler(EventHandler):
    """Main event handler that routes events to appropriate bots."""

    def __init__(self, db, redis, neo4j, rag, llm):
        self.db = db
        self.redis = redis
        self.neo4j = neo4j
        self.rag = rag
        self.llm = llm

    async def handle(self, topic: str, payload: dict) -> None:
        """Route events to appropriate handlers."""
        from uuid import UUID

        startup_id = payload.get("startup_id")
        if startup_id:
            startup_id = UUID(startup_id)

        handlers = {
            "startup.stress.high": self._handle_high_stress,
            "startup.obituary.high_match": self._handle_obituary_match,
            "termsheet.red_flag": self._handle_termsheet_red_flag,
            "startup.pivot.detected": self._handle_pivot_detected,
            "startup.pmf.inflection": self._handle_pmf_inflection,
            "investor.network.updated": self._handle_network_update,
            "startup.acqui.signal": self._handle_acqui_signal,
        }

        handler = handlers.get(topic)
        if handler:
            await handler(startup_id, payload)
        else:
            logger.warning(f"No handler for topic: {topic}")

    async def _handle_high_stress(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle high stress events - trigger PivotBot and ObituaryBot."""
        logger.info(f"High stress detected for {startup_id}: score={payload.get('score')}")
        # Could trigger downstream bot runs here

    async def _handle_obituary_match(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle obituary high match events."""
        logger.info(f"Obituary match for {startup_id}: {payload.get('top_match')}")

    async def _handle_termsheet_red_flag(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle term sheet red flag events."""
        logger.info(f"Term sheet red flags for {startup_id}: {payload.get('red_flags')}")

    async def _handle_pivot_detected(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle pivot detection events."""
        logger.info(f"Pivot detected for {startup_id}: {payload.get('pivot_confidence')}")

    async def _handle_pmf_inflection(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle PMF inflection events."""
        logger.info(f"PMF inflection for {startup_id}: score={payload.get('pmf_score')}")

    async def _handle_network_update(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle investor network update events."""
        logger.info(f"Network updated: {payload.get('investor_id')}")

    async def _handle_acqui_signal(self, startup_id: UUID | None, payload: dict) -> None:
        """Handle acqui-hire signal events."""
        logger.info(f"Acqui signal for {startup_id}: probability={payload.get('probability')}")


class MultiConsumerManager:
    """Manager for running multiple Kafka consumers."""

    def __init__(self):
        self.consumers: list[KafkaEventConsumer] = []

    def add_consumer(self, consumer: KafkaEventConsumer) -> None:
        """Add a consumer to the manager."""
        self.consumers.append(consumer)

    async def start_all(self) -> None:
        """Start all consumers."""
        import asyncio

        await asyncio.gather(*[c.start() for c in self.consumers], return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all consumers."""
        await asyncio.gather(*[c.stop() for c in self.consumers], return_exceptions=True)
