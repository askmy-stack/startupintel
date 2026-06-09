from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from startupintel.events.topics import TERMSHEET_RED_FLAG


RISK_SCORE = {"low": 1.0, "medium": 0.5, "high": 0.0}

CLAUSES = {
    "liquidation_preference": {
        "weight": 0.20,
        "red_flags": ["participating preferred", "2x liquidation", "3x liquidation"],
        "standard": "1x non-participating",
    },
    "anti_dilution": {
        "weight": 0.15,
        "red_flags": ["full ratchet"],
        "standard": "broad-based weighted average",
    },
    "board_composition": {
        "weight": 0.15,
        "red_flags": ["investor majority"],
        "standard": "2F 2I 1 independent",
    },
    "option_pool_shuffle": {
        "weight": 0.12,
        "red_flags": ["pre-money option pool", "pre money option pool"],
        "standard": "post-money",
    },
    "drag_along": {
        "weight": 0.10,
        "red_flags": ["drag along threshold 40", "drag-along threshold 40"],
        "standard": "majority common + majority preferred",
    },
    "vesting_schedule": {
        "weight": 0.08,
        "red_flags": ["no acceleration", "24 month cliff"],
        "standard": "4yr/1yr cliff, double trigger",
    },
    "pay_to_play": {
        "weight": 0.07,
        "red_flags": ["pay to play without founder carveout"],
        "standard": "absent or with founder carveout",
    },
    "pro_rata_rights": {
        "weight": 0.05,
        "red_flags": ["super pro rata", "super pro-rata"],
        "standard": "standard pro rata",
    },
    "information_rights": {
        "weight": 0.03,
        "red_flags": ["no information rights", "information rights absent"],
        "standard": "quarterly + annual audited",
    },
    "right_of_first_refusal": {
        "weight": 0.02,
        "red_flags": ["right of first offer"],
        "standard": "standard ROFR",
    },
    "co_sale_rights": {
        "weight": 0.02,
        "red_flags": ["co-sale no founder carveout"],
        "standard": "with founder carveout <=10%",
    },
    "valuation_cap": {
        "weight": 0.01,
        "red_flags": ["valuation cap below"],
        "standard": "context dependent",
    },
}


@dataclass(frozen=True)
class ClauseAnalysis:
    detected_value: str
    is_market_standard: bool
    risk_level: str
    explanation: str
    founder_impact: str
    weight: float
    score: float


@dataclass(frozen=True)
class TermBotResult:
    analysis_id: UUID
    startup_id: UUID | None
    founder_friendliness_score: float
    market_benchmark_score: float
    red_flags: list[str]
    yellow_flags: list[str]
    clause_scores: dict[str, ClauseAnalysis]
    llm_diagnosis: str
    analyzed_at: datetime


class TermBot:
    name = "term"

    def __init__(self, producer=None):
        self.producer = producer

    def analyze_clause(self, clause_name: str, text: str) -> ClauseAnalysis:
        clause = CLAUSES[clause_name]
        lowered = text.lower()
        matched = [flag for flag in clause["red_flags"] if flag in lowered]
        risk_level = "high" if matched else ("medium" if clause_name not in lowered else "low")
        return ClauseAnalysis(
            detected_value=matched[0] if matched else clause["standard"],
            is_market_standard=risk_level == "low",
            risk_level=risk_level,
            explanation=f"{clause_name} assessed as {risk_level}.",
            founder_impact="High risk reduces founder control or economics."
            if risk_level == "high"
            else "No material founder impact detected.",
            weight=clause["weight"],
            score=RISK_SCORE[risk_level],
        )

    async def analyze_text(self, text: str, startup_id: UUID | None = None) -> TermBotResult:
        clause_scores = {name: self.analyze_clause(name, text) for name in CLAUSES}
        score = round(
            sum(analysis.weight * analysis.score for analysis in clause_scores.values()) * 100,
            2,
        )
        red_flags = [name for name, analysis in clause_scores.items() if analysis.risk_level == "high"]
        yellow_flags = [name for name, analysis in clause_scores.items() if analysis.risk_level == "medium"]
        result = TermBotResult(
            analysis_id=uuid4(),
            startup_id=startup_id,
            founder_friendliness_score=score,
            market_benchmark_score=score,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            clause_scores=clause_scores,
            llm_diagnosis=f"Founder-friendliness score is {score}/100 with {len(red_flags)} red flags.",
            analyzed_at=datetime.now(UTC),
        )
        if red_flags and self.producer is not None:
            await self.producer.emit(TERMSHEET_RED_FLAG, {"red_flags": red_flags, "score": score})
        return result

