from collections import Counter, defaultdict
from uuid import UUID

from startupintel.bots.base import BaseBot, BotResult
from startupintel.events.topics import INVESTOR_NETWORK_UPDATED
from startupintel.scoring.normalizer import clamp


WEIGHTS = {
    "betweenness": 0.35,
    "eigenvector": 0.25,
    "diversity": 0.20,
    "value_add_proxy": 0.20,
}


class InvestorBot(BaseBot):
    name = "investor"
    required_signals = list(WEIGHTS)

    async def fetch_signals(self, startup_id: UUID) -> dict:
        raise NotImplementedError("InvestorBot fetch_signals requires investor graph connectors.")

    async def compute_score(self, raw: dict) -> dict[str, float]:
        return {
            "betweenness": clamp(float(raw.get("betweenness", raw.get("betweenness_percentile", 0.0)))),
            "eigenvector": clamp(float(raw.get("eigenvector", raw.get("eigenvector_percentile", 0.0)))),
            "diversity": clamp(float(raw.get("diversity", raw.get("portfolio_diversity_score", 0.0)))),
            "value_add_proxy": clamp(float(raw.get("value_add_proxy", raw.get("value_add_proxy_score", 0.0)))),
        }

    def get_weights(self) -> dict[str, float]:
        return WEIGHTS

    def build_rag_query(self, raw: dict) -> str:
        return f"investor network value {raw.get('name', '')} {raw.get('firm', '')}"

    def diagnosis_prompt_template(self) -> str:
        return "Explain investor centrality, bridge value, diversity, and value-add proxy."

    def diversity_score(self, labels: list[str]) -> float:
        if not labels:
            return 0.0
        counts = Counter(labels)
        concentration = sum((count / len(labels)) ** 2 for count in counts.values())
        return round(1.0 - concentration, 4)

    def project_co_investor_graph(self, deals: list[dict]) -> dict[str, set[str]]:
        by_startup: dict[str, list[str]] = defaultdict(list)
        for deal in deals:
            by_startup[deal["startup_id"]].extend(deal.get("investor_ids", []))
        graph: dict[str, set[str]] = defaultdict(set)
        for investors in by_startup.values():
            for investor in investors:
                graph[investor].update(other for other in investors if other != investor)
        return dict(graph)

    async def maybe_emit_event(self, result: BotResult) -> None:
        previous = float(result.raw_signals.get("previous_centrality_score", result.score))
        if abs(result.score - previous) <= 10 or self.producer is None:
            return
        await self.producer.emit(INVESTOR_NETWORK_UPDATED, {"investor_id": str(result.startup_id), "score": result.score})

