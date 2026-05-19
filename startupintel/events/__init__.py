"""Event topic, producer, and consumer utilities."""

from startupintel.events.producer import (
    InMemoryEventProducer,
    KafkaEventProducer,
    get_event_producer,
    set_event_producer,
)
from startupintel.events.consumer import (
    EventHandler,
    KafkaEventConsumer,
    StartupIntelEventHandler,
    MultiConsumerManager,
)
from startupintel.events import topics

__all__ = [
    # Producers
    "InMemoryEventProducer",
    "KafkaEventProducer",
    "get_event_producer",
    "set_event_producer",
    # Consumers
    "EventHandler",
    "KafkaEventConsumer",
    "StartupIntelEventHandler",
    "MultiConsumerManager",
    # Topics module
    "topics",
]
