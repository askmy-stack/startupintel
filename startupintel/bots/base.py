from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

from startupintel.db.models import StartupScore


@dataclass
class BotResult:
    startup_id: UUID
    bot_name: str
    score: float
    signal_breakdown: dict[str, float]
    raw_signals: dict
    similar_cases: list[dict]
    llm_diagnosis: str
    computed_at: datetime


class BaseBot(ABC):
    name: str
    version: str = "0.1.0"
    required_signals: list[str] = []

    def __init__(self, db=None, neo4j=None, redis=None, rag_retriever=None, llm_client=None, producer=None):
        self.db = db
        self.neo4j = neo4j
        self.redis = redis
        self.rag = rag_retriever
        self.llm = llm_client
        self.producer = producer

    def cache_key(self, startup_id: UUID) -> str:
        return f"{self.name}:{self.version}:{startup_id}"

    async def run(self, startup_id: UUID) -> BotResult:
        cache_key = self.cache_key(startup_id)
        cached = await self._get_cached(cache_key)
        if cached:
            return BotResult(**cached)

        raw_signals = await self.fetch_signals(startup_id)
        signal_breakdown = await self.compute_score(raw_signals)
        score = self.normalize(signal_breakdown)
        similar_cases = await self._search_similar_cases(raw_signals)
        diagnosis = await self._diagnose(score, signal_breakdown, similar_cases, raw_signals)
        result = BotResult(
            startup_id=startup_id,
            bot_name=self.name,
            score=score,
            signal_breakdown=signal_breakdown,
            raw_signals=raw_signals,
            similar_cases=similar_cases,
            llm_diagnosis=diagnosis,
            computed_at=datetime.now(UTC),
        )
        await self.persist(result)
        await self.write_to_graph(result)
        await self._set_cached(cache_key, result)
        await self.maybe_emit_event(result)
        return result

    def normalize(self, signal_breakdown: dict[str, float]) -> float:
        weights = self.get_weights()
        raw = sum(signal_breakdown.get(key, 0.0) * weight for key, weight in weights.items())
        return round(min(100.0, max(0.0, raw * 100)), 2)

    async def persist(self, result: BotResult) -> None:
        if self.db is None:
            return
        self.db.add(
            StartupScore(
                startup_id=result.startup_id,
                bot_name=result.bot_name,
                score=result.score,
                signal_breakdown=result.signal_breakdown,
                raw_signals=result.raw_signals,
                similar_cases=result.similar_cases,
                llm_diagnosis=result.llm_diagnosis,
                computed_at=result.computed_at,
            )
        )
        await self.db.commit()

    async def write_to_graph(self, result: BotResult) -> None:
        if self.neo4j is None:
            return
        property_name = f"{self.name}_score"
        async with self.neo4j.session() as session:
            await session.run(
                f"MATCH (s:Startup {{id: $startup_id}}) SET s.{property_name} = $score",
                startup_id=str(result.startup_id),
                score=result.score,
            )

    async def _get_cached(self, cache_key: str) -> dict | None:
        if self.redis is None:
            return None
        cached = await self.redis.get(cache_key)
        return cached if isinstance(cached, dict) else None

    async def _set_cached(self, cache_key: str, result: BotResult) -> None:
        if self.redis is None:
            return
        await self.redis.setex(cache_key, 3600, asdict(result))

    async def _search_similar_cases(self, raw: dict) -> list[dict]:
        if self.rag is None:
            return []
        return await self.rag.search(self.build_rag_query(raw), top_k=5)

    async def _diagnose(
        self,
        score: float,
        signal_breakdown: dict[str, float],
        similar_cases: list[dict],
        raw_signals: dict,
    ) -> str:
        if self.llm is None:
            return "Diagnosis unavailable: no LLM client configured."
        return await self.llm.generate_diagnosis(
            self.name,
            score,
            signal_breakdown,
            similar_cases,
            self.diagnosis_prompt_template(),
            raw_signals=raw_signals,
        )

    @abstractmethod
    async def fetch_signals(self, startup_id: UUID) -> dict: ...

    @abstractmethod
    async def compute_score(self, raw: dict) -> dict[str, float]: ...

    @abstractmethod
    def get_weights(self) -> dict[str, float]: ...

    @abstractmethod
    def build_rag_query(self, raw: dict) -> str: ...

    @abstractmethod
    def diagnosis_prompt_template(self) -> str: ...

    @abstractmethod
    async def maybe_emit_event(self, result: BotResult) -> None: ...
