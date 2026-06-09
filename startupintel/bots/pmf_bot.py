from datetime import datetime
from uuid import UUID

from startupintel.bots.base import BaseBot, BotResult
from startupintel.events.topics import STARTUP_PMF_INFLECTION
from startupintel.scoring.normalizer import clamp


WEIGHTS = {
    "app_store_review_velocity": 0.25,
    "g2_rating_trajectory": 0.20,
    "organic_search_growth": 0.20,
    "github_star_acceleration": 0.15,
    "stackoverflow_volume": 0.10,
    "reddit_mention_sentiment": 0.05,
    "producthunt_upvote_rate": 0.03,
    "twitter_mention_growth": 0.02,
}


class PMFBot(BaseBot):
    name = "pmf"
    required_signals = list(WEIGHTS)

    async def fetch_signals(self, startup_id: UUID) -> dict:
        raise NotImplementedError("PMFBot fetch_signals requires PMF connectors.")

    async def compute_score(self, raw: dict) -> dict[str, float]:
        return {signal: clamp(float(raw.get(signal, 0.0))) for signal in WEIGHTS}

    def get_weights(self) -> dict[str, float]:
        return WEIGHTS

    def build_rag_query(self, raw: dict) -> str:
        return f"product market fit signals {raw}"

    def diagnosis_prompt_template(self) -> str:
        return "Explain PMF status, strongest signal, weakest signal, and changepoint."

    def pmf_status(self, score: float) -> str:
        if score <= 30:
            return "pre_pmf"
        if score <= 60:
            return "approaching"
        if score <= 80:
            return "strong"
        return "clear"

    def strongest_signal(self, signal_breakdown: dict[str, float]) -> str:
        return max(signal_breakdown, key=signal_breakdown.get)

    def weakest_signal(self, signal_breakdown: dict[str, float]) -> str:
        return min(signal_breakdown, key=signal_breakdown.get)

    def detect_changepoint(self, series: list[dict], threshold: float = 15.0) -> tuple[bool, datetime | None]:
        if len(series) < 4:
            return False, None
        scores = [float(point["score"]) for point in series]
        prior_avg = sum(scores[:-1]) / (len(scores) - 1)
        if scores[-1] - prior_avg >= threshold:
            date = series[-1].get("date")
            return True, datetime.fromisoformat(date) if isinstance(date, str) else date
        return False, None

    async def maybe_emit_event(self, result: BotResult) -> None:
        history = result.raw_signals.get("score_history", [])
        changepoint, _ = self.detect_changepoint(history)
        if (result.score <= 60 and not changepoint) or self.producer is None:
            return
        await self.producer.emit(STARTUP_PMF_INFLECTION, {"startup_id": str(result.startup_id), "score": result.score})

