from uuid import uuid4

import pytest

from startupintel.bots.pmf_bot import PMFBot, WEIGHTS
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import STARTUP_PMF_INFLECTION


class StaticPMFBot(PMFBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


@pytest.mark.asyncio
async def test_high_pmf_known_startup_emits_event():
    producer = InMemoryEventProducer()
    bot = StaticPMFBot({signal: 0.9 for signal in WEIGHTS}, producer=producer)
    result = await bot.run(uuid4())
    assert result.score == 90
    assert bot.pmf_status(result.score) == "clear"
    assert producer.events[0][0] == STARTUP_PMF_INFLECTION


def test_changepoint_detected_from_score_history():
    bot = StaticPMFBot({})
    detected, date = bot.detect_changepoint(
        [
            {"date": "2026-01-01T00:00:00", "score": 30},
            {"date": "2026-01-08T00:00:00", "score": 32},
            {"date": "2026-01-15T00:00:00", "score": 34},
            {"date": "2026-01-22T00:00:00", "score": 72},
        ]
    )
    assert detected is True
    assert date is not None

