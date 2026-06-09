from uuid import uuid4

import pytest

from startupintel.bots.obituary_bot import ObituaryBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import STARTUP_OBITUARY_HIGH_MATCH


class StaticObituaryBot(ObituaryBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


@pytest.mark.asyncio
async def test_high_similarity_known_failure_emits_event():
    producer = InMemoryEventProducer()
    bot = StaticObituaryBot(
        {
            "similar_cases": [
                {"name": "Quibi", "similarity": 0.91, "failure_cause": "no_market_need"},
                {"name": "Homejoy", "similarity": 0.84, "failure_cause": "no_market_need"},
                {"name": "Beepi", "similarity": 0.78, "failure_cause": "ran_out_of_cash"},
            ]
        },
        producer=producer,
    )
    result = await bot.run(uuid4())
    assert result.score > 70
    assert producer.events[0][0] == STARTUP_OBITUARY_HIGH_MATCH
    assert bot.top_failure_pattern(result.raw_signals["similar_cases"])[0] == "no_market_need"


@pytest.mark.asyncio
async def test_low_similarity_healthy_startup():
    bot = StaticObituaryBot({"similar_cases": [{"name": "Example", "similarity": 0.12}]})
    result = await bot.run(uuid4())
    assert result.score < 30

