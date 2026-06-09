from uuid import uuid4

import pytest

from startupintel.bots.acqui_bot import AcquiBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import STARTUP_ACQUI_SIGNAL


class StaticAcquiBot(AcquiBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


HIGH_TEAM = {
    "faang_alumni_ratio": 0.8,
    "top10_uni_ratio": 0.7,
    "founder_prior_exit": 1,
    "avg_years_experience": 12,
    "tech_stack_rarity_score": 0.85,
    "personal_repo_stars": 4200,
    "investor_acquirer_overlap": 0.7,
    "linkedin_connections_at_acquirers": 80,
    "runway_stress_score": 72,
    "months_since_last_raise": 18,
}


@pytest.mark.asyncio
async def test_high_team_raises_probability_and_emits_event():
    producer = InMemoryEventProducer()
    bot = StaticAcquiBot(HIGH_TEAM, producer=producer)
    result = await bot.run(uuid4())
    assert result.score > 70
    assert producer.events[0][0] == STARTUP_ACQUI_SIGNAL


def test_5_acquirers_returned_and_ranked():
    bot = StaticAcquiBot({})
    acquirers = bot.likely_acquirers()
    assert len(acquirers) == 5
    assert acquirers[0]["fit_score"] >= acquirers[-1]["fit_score"]


def test_feature_importances_sum_to_one():
    bot = StaticAcquiBot({})
    importances = bot.feature_importances(HIGH_TEAM)
    assert round(sum(importances.values()), 2) == 1.0

