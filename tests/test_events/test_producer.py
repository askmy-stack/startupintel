"""Tests for event producers."""

from __future__ import annotations

import pytest

from startupintel.events.producer import InMemoryEventProducer, KafkaEventProducer, get_event_producer, set_event_producer


@pytest.mark.asyncio
async def test_in_memory_event_producer():
    """Test in-memory event producer."""
    producer = InMemoryEventProducer()

    # Test emit
    await producer.emit("test.topic", {"key": "value"})
    assert len(producer.events) == 1
    assert producer.events[0] == ("test.topic", {"key": "value"})

    # Test start/stop (no-ops)
    await producer.start()
    await producer.stop()


@pytest.mark.asyncio
async def test_event_producer_singleton():
    """Test event producer singleton pattern."""
    # Clear any existing producer
    set_event_producer(None)

    # Get default (should return InMemoryEventProducer)
    producer = get_event_producer()
    assert isinstance(producer, InMemoryEventProducer)

    # Set custom producer
    custom = InMemoryEventProducer()
    set_event_producer(custom)
    assert get_event_producer() is custom


@pytest.mark.asyncio
async def test_kafka_producer_init():
    """Test Kafka producer initialization."""
    # This just tests initialization without actually connecting
    producer = KafkaEventProducer(
        bootstrap_servers="localhost:9092",
        client_id="test-producer",
    )

    assert producer.bootstrap_servers == "localhost:9092"
    assert producer.client_id == "test-producer"
    assert producer._producer is None
