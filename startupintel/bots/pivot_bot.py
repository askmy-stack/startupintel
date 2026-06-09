from datetime import UTC, datetime
from uuid import UUID

from startupintel.bots.base import BaseBot, BotResult
from startupintel.events.topics import STARTUP_PIVOT_DETECTED
from startupintel.scoring.normalizer import clamp


PIVOT_TYPES = {"customer_segment", "product", "revenue_model", "technology", "geography"}


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PivotBot(BaseBot):
    name = "pivot"
    required_signals = ["pivot_events"]

    async def fetch_signals(self, startup_id: UUID) -> dict:
        raise NotImplementedError("PivotBot fetch_signals requires pivot connectors.")

    async def compute_score(self, raw: dict) -> dict[str, float]:
        events = self.deduplicate_events(raw.get("pivot_events", []))
        confidences = [float(event.get("confidence", 0.0)) for event in events]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return {
            "pivot_count_normalized": clamp(len(events) / 3.0),
            "avg_confidence": clamp(avg_confidence),
            "recency": self.recency_score(events),
        }

    def get_weights(self) -> dict[str, float]:
        return {"pivot_count_normalized": 0.50, "avg_confidence": 0.30, "recency": 0.20}

    def build_rag_query(self, raw: dict) -> str:
        return " ".join(event.get("evidence_summary", "") for event in raw.get("pivot_events", []))

    def diagnosis_prompt_template(self) -> str:
        return "Summarize the detected pivot timeline and the strongest evidence."

    def deduplicate_events(self, events: list[dict]) -> list[dict]:
        sorted_events = sorted(events, key=lambda event: parse_datetime(event["date"]))
        deduped: list[dict] = []
        for event in sorted_events:
            event_date = parse_datetime(event["date"])
            if deduped and (event_date - parse_datetime(deduped[-1]["date"])).days <= 30:
                if float(event.get("confidence", 0.0)) > float(deduped[-1].get("confidence", 0.0)):
                    deduped[-1] = event
                continue
            deduped.append(event)
        return deduped

    def recency_score(self, events: list[dict]) -> float:
        if not events:
            return 0.0
        newest = max(parse_datetime(event["date"]) for event in events)
        days_old = (datetime.now(UTC) - newest).days
        return clamp((365 - days_old) / 365)

    def primary_pivot_type(self, events: list[dict]) -> str | None:
        valid = [event.get("pivot_type") for event in events if event.get("pivot_type") in PIVOT_TYPES]
        if not valid:
            return None
        return max(set(valid), key=valid.count)

    async def maybe_emit_event(self, result: BotResult) -> None:
        if not result.raw_signals.get("pivot_events") or self.producer is None:
            return
        await self.producer.emit(STARTUP_PIVOT_DETECTED, {"startup_id": str(result.startup_id), "score": result.score})

