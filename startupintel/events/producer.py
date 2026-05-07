from dataclasses import dataclass, field


@dataclass
class InMemoryEventProducer:
    """Test-friendly producer used until Kafka wiring is enabled."""

    events: list[tuple[str, dict]] = field(default_factory=list)

    async def emit(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))

