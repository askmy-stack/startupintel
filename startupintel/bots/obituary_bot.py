from collections import Counter
from uuid import UUID

from startupintel.bots.base import BaseBot, BotResult
from startupintel.events.topics import STARTUP_OBITUARY_HIGH_MATCH
from startupintel.scoring.normalizer import clamp


FAILURE_TAXONOMY = {
    "no_market_need",
    "ran_out_of_cash",
    "wrong_team",
    "competition",
    "pricing_model",
    "poor_product",
    "bad_timing",
    "pivot_failure",
    "legal_regulatory",
    "burnout",
    "failed_to_raise",
    "founder_conflict",
}


class ObituaryBot(BaseBot):
    name = "obituary"
    required_signals = ["similar_cases"]

    async def fetch_signals(self, startup_id: UUID) -> dict:
        raise NotImplementedError("ObituaryBot fetch_signals requires RAG corpus wiring.")

    async def compute_score(self, raw: dict) -> dict[str, float]:
        cases = raw.get("similar_cases", [])
        similarities = [float(case.get("similarity", case.get("score", 0.0))) for case in cases]
        top_match = max(similarities, default=float(raw.get("top_match_similarity", 0.0)))
        avg_top3 = (
            sum(sorted(similarities, reverse=True)[:3]) / min(3, len(similarities))
            if similarities
            else float(raw.get("avg_top3_similarity", 0.0))
        )
        causes = [case.get("failure_cause") for case in cases[:5] if case.get("failure_cause")]
        cause_concentration = (
            1.0 - (len(set(causes)) / 5.0)
            if causes
            else float(raw.get("cause_concentration", 0.0))
        )
        return {
            "top_match_similarity": clamp(top_match),
            "avg_top3_similarity": clamp(avg_top3),
            "cause_concentration": clamp(cause_concentration),
        }

    def get_weights(self) -> dict[str, float]:
        return {"top_match_similarity": 0.50, "avg_top3_similarity": 0.30, "cause_concentration": 0.20}

    def build_rag_query(self, raw: dict) -> str:
        return " ".join(
            str(part)
            for part in [raw.get("industry"), raw.get("stage"), raw.get("failure_signals_summary")]
            if part
        )

    def diagnosis_prompt_template(self) -> str:
        return (
            "Startup: {name} | Industry: {industry} | Stage: {stage}\n"
            "Current signals: {failure_signals_summary}\n"
            "Top 3 similar historical failures: {similar_cases}\n"
            "Write 3 specific sentences naming comparable companies."
        )

    def taxonomy_breakdown(self, similar_cases: list[dict]) -> dict[str, int]:
        counter = Counter(
            case.get("failure_cause")
            for case in similar_cases
            if case.get("failure_cause") in FAILURE_TAXONOMY
        )
        return dict(counter)

    def top_failure_pattern(self, similar_cases: list[dict]) -> tuple[str, float]:
        breakdown = self.taxonomy_breakdown(similar_cases)
        if not breakdown:
            return "unknown", 0.0
        pattern, count = max(breakdown.items(), key=lambda item: item[1])
        return pattern, round(count / max(1, len(similar_cases)), 2)

    async def maybe_emit_event(self, result: BotResult) -> None:
        if result.score <= 70 or self.producer is None:
            return
        await self.producer.emit(
            STARTUP_OBITUARY_HIGH_MATCH,
            {"startup_id": str(result.startup_id), "score": result.score},
        )

