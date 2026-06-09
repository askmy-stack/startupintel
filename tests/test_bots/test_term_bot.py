import pytest

from startupintel.bots.term_bot import CLAUSES, TermBot
from startupintel.events.producer import InMemoryEventProducer
from startupintel.events.topics import TERMSHEET_RED_FLAG


@pytest.mark.asyncio
async def test_founder_friendly_termsheet_scores_high():
    text = " ".join(f"{name} {clause['standard']}" for name, clause in CLAUSES.items())
    result = await TermBot().analyze_text(text)
    assert result.founder_friendliness_score == 100
    assert result.red_flags == []
    assert len(result.clause_scores) == 12


@pytest.mark.asyncio
async def test_predatory_termsheet_flags_clauses_and_emits_event():
    producer = InMemoryEventProducer()
    result = await TermBot(producer=producer).analyze_text(
        "2x liquidation full ratchet investor majority super pro rata"
    )
    assert result.founder_friendliness_score < 70
    assert {"liquidation_preference", "anti_dilution", "board_composition"} <= set(result.red_flags)
    assert producer.events[0][0] == TERMSHEET_RED_FLAG

