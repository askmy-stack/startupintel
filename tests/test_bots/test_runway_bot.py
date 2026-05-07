from uuid import uuid4

import pytest

from startupintel.bots.runway_bot import RunwayBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import STARTUP_STRESS_HIGH


class StaticRunwayBot(RunwayBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


@pytest.mark.asyncio
async def test_low_stress_score():
    bot = StaticRunwayBot(
        {
            "headcount_delta_pct": 0.3,
            "job_posting_delta_pct": 0.5,
            "founder_sentiment": 0.8,
            "domain_expiry_days": 365,
            "days_since_funding": 120,
        }
    )
    result = await bot.run(uuid4())
    assert result.score < 30
    assert bot.risk_level(result.score) == "low"


@pytest.mark.asyncio
async def test_high_stress_emits_event():
    producer = InMemoryEventProducer()
    bot = StaticRunwayBot(
        {
            "headcount_delta_pct": -0.3,
            "job_posting_delta_pct": -0.8,
            "founder_sentiment": -0.7,
            "domain_expiry_days": 10,
            "days_since_funding": 800,
        },
        producer=producer,
    )
    result = await bot.run(uuid4())
    assert result.score > 65
    assert producer.events[0][0] == STARTUP_STRESS_HIGH


@pytest.mark.asyncio
async def test_missing_signal_defaults_are_degraded_not_fatal():
    bot = StaticRunwayBot({"headcount_delta_pct": -0.2})
    result = await bot.run(uuid4())
    assert set(result.signal_breakdown) == set(bot.get_weights())

