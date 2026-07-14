from datetime import UTC, datetime
from uuid import uuid4

import pytest

from startupintel.bots.base import BaseBot, BotResult


class _StubBot(BaseBot):
    """Minimal concrete BaseBot for exercising write_to_graph directly."""

    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def fetch_signals(self, startup_id):
        return {}

    async def compute_score(self, raw):
        return {}

    def get_weights(self):
        return {}

    def build_rag_query(self, raw):
        return ""

    def diagnosis_prompt_template(self):
        return ""

    async def maybe_emit_event(self, result):
        return None


class _FakeSession:
    def __init__(self, calls: list):
        self._calls = calls

    async def run(self, query, **params):
        self._calls.append((query, params))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class _FakeNeo4jDriver:
    def __init__(self):
        self.calls: list = []

    def session(self):
        return _FakeSession(self.calls)


def _make_result(bot_name: str) -> BotResult:
    return BotResult(
        startup_id=uuid4(),
        bot_name=bot_name,
        score=42.0,
        signal_breakdown={},
        raw_signals={},
        similar_cases=[],
        llm_diagnosis="",
        computed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_write_to_graph_uses_expected_property_name():
    driver = _FakeNeo4jDriver()
    bot = _StubBot("runway", neo4j=driver)
    result = _make_result("runway")

    await bot.write_to_graph(result)

    assert len(driver.calls) == 1
    query, params = driver.calls[0]
    assert "s.runway_score" in query
    assert params["score"] == 42.0


@pytest.mark.asyncio
async def test_write_to_graph_skips_when_neo4j_not_configured():
    bot = _StubBot("runway", neo4j=None)
    result = _make_result("runway")

    await bot.write_to_graph(result)  # should not raise


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malicious_name",
    [
        "runway`}) DETACH DELETE s //",
        "runway} SET s.pwned = true MATCH (x",
        "runway; DROP",
        "runway score",
        "Runway",
        "",
    ],
)
async def test_write_to_graph_rejects_unsafe_bot_names(malicious_name):
    driver = _FakeNeo4jDriver()
    bot = _StubBot(malicious_name, neo4j=driver)
    result = _make_result(malicious_name)

    with pytest.raises(ValueError, match="Unsafe Neo4j property name"):
        await bot.write_to_graph(result)

    assert driver.calls == []
