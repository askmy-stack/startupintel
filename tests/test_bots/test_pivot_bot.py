from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from startupintel.bots.pivot_bot import PivotBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import STARTUP_PIVOT_DETECTED


class StaticPivotBot(PivotBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


@pytest.mark.asyncio
async def test_known_pivot_detected_and_emitted():
    now = datetime.now(UTC)
    producer = InMemoryEventProducer()
    bot = StaticPivotBot(
        {
            "pivot_events": [
                {
                    "date": (now - timedelta(days=10)).isoformat(),
                    "source": "wayback",
                    "pivot_type": "product",
                    "confidence": 0.9,
                    "evidence_summary": "Homepage moved from consumer to enterprise.",
                }
            ]
        },
        producer=producer,
    )
    result = await bot.run(uuid4())
    assert result.score > 40
    assert bot.primary_pivot_type(result.raw_signals["pivot_events"]) == "product"
    assert producer.events[0][0] == STARTUP_PIVOT_DETECTED


def test_deduplication_keeps_highest_confidence_within_30_days():
    now = datetime.now(UTC)
    bot = StaticPivotBot({"pivot_events": []})
    events = [
        {"date": now.isoformat(), "confidence": 0.4},
        {"date": (now + timedelta(days=5)).isoformat(), "confidence": 0.8},
    ]
    assert bot.deduplicate_events(events)[0]["confidence"] == 0.8

