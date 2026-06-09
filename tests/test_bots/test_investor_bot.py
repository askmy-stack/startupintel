from uuid import uuid4

import pytest

from startupintel.bots.investor_bot import InvestorBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import INVESTOR_NETWORK_UPDATED


class StaticInvestorBot(InvestorBot):
    def __init__(self, signals: dict, **kwargs):
        super().__init__(**kwargs)
        self.signals = signals

    async def fetch_signals(self, startup_id):
        return self.signals


@pytest.mark.asyncio
async def test_central_investor_scores_high_and_emits_on_delta():
    producer = InMemoryEventProducer()
    bot = StaticInvestorBot(
        {
            "betweenness": 0.9,
            "eigenvector": 0.8,
            "diversity": 0.7,
            "value_add_proxy": 0.9,
            "previous_centrality_score": 40,
        },
        producer=producer,
    )
    result = await bot.run(uuid4())
    assert result.score > 80
    assert producer.events[0][0] == INVESTOR_NETWORK_UPDATED


def test_graph_projection_valid():
    bot = StaticInvestorBot({})
    graph = bot.project_co_investor_graph(
        [
            {"startup_id": "s1", "investor_ids": ["i1", "i2"]},
            {"startup_id": "s2", "investor_ids": ["i2", "i3"]},
        ]
    )
    assert graph["i2"] == {"i1", "i3"}


def test_diversity_gini_proxy():
    bot = StaticInvestorBot({})
    assert bot.diversity_score(["saas", "fintech", "health"]) > bot.diversity_score(["saas", "saas", "saas"])

