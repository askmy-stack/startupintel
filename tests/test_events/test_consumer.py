"""Tests for event consumers."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock

from startupintel.events.consumer import EventHandler, KafkaEventConsumer, MultiConsumerManager


class MockEventHandler(EventHandler):
    """Mock event handler for testing."""

    def __init__(self):
        self.handled_events = []

    async def handle(self, topic: str, payload: dict) -> None:
        self.handled_events.append((topic, payload))


@pytest.mark.asyncio
async def test_event_handler():
    """Test event handler base class."""
    handler = MockEventHandler()

    await handler.handle("test.topic", {"key": "value"})
    assert len(handler.handled_events) == 1
    assert handler.handled_events[0] == ("test.topic", {"key": "value"})


@pytest.mark.asyncio
async def test_multi_consumer_manager():
    """Test multi-consumer manager."""
    manager = MultiConsumerManager()

    # Create mock consumers
    mock_consumer1 = Mock()
    mock_consumer1.start = AsyncMock()
    mock_consumer1.stop = AsyncMock()

    mock_consumer2 = Mock()
    mock_consumer2.start = AsyncMock()
    mock_consumer2.stop = AsyncMock()

    # Add consumers
    manager.add_consumer(mock_consumer1)
    manager.add_consumer(mock_consumer2)

    assert len(manager.consumers) == 2

    # Test start_all
    await manager.start_all()
    mock_consumer1.start.assert_called_once()
    mock_consumer2.start.assert_called_once()

    # Test stop_all
    await manager.stop_all()
    mock_consumer1.stop.assert_called_once()
    mock_consumer2.stop.assert_called_once()


def test_kafka_consumer_init():
    """Test Kafka consumer initialization."""
    handler = MockEventHandler()

    consumer = KafkaEventConsumer(
        bootstrap_servers="localhost:9092",
        group_id="test-group",
        topics=["test.topic"],
        handler=handler,
    )

    assert consumer.bootstrap_servers == "localhost:9092"
    assert consumer.group_id == "test-group"
    assert consumer.topics == ["test.topic"]
    assert consumer.handler is handler
    assert not consumer._running
