from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from uuid import UUID

from startupintel.scoring.normalizer import clamp


METRICS = {
    "follow_on_funding_rate": 0.30,
    "median_time_to_series_a_months": 0.20,
    "survival_rate_3yr": 0.20,
    "unicorn_rate": 0.15,
    "acqui_hire_rate": 0.10,
    "shutdown_rate": -0.05,
}


@dataclass(frozen=True)
class AcceleratorBotResult:
    accelerator_id: UUID
    name: str
    roi_score: float
    global_rank: int
    industry_rank: int
    geo_rank: int
    raw_metrics: dict[str, float]
    normalized_metrics: dict[str, float]
    cohort_count: int
    cohort_companies_analyzed: int
    confidence_interval: tuple[float, float]
    peer_comparison: list[dict]
    computed_at: datetime


class AcceleratorBot:
    name = "accelerator"
    minimum_cohort_size = 10

    def normalize_metrics(self, metrics: dict[str, float]) -> dict[str, float]:
        months = float(metrics.get("median_time_to_series_a_months", 36.0))
        return {
            "follow_on_funding_rate": clamp(float(metrics.get("follow_on_funding_rate", 0.0))),
            "median_time_to_series_a_months": clamp((36.0 - months) / 36.0),
            "survival_rate_3yr": clamp(float(metrics.get("survival_rate_3yr", 0.0))),
            "unicorn_rate": clamp(float(metrics.get("unicorn_rate", 0.0))),
            "acqui_hire_rate": clamp(float(metrics.get("acqui_hire_rate", 0.0))),
            "shutdown_rate": clamp(float(metrics.get("shutdown_rate", 0.0))),
        }

    def compute_roi_score(self, metrics: dict[str, float], cohort_count: int) -> float:
        if cohort_count < self.minimum_cohort_size:
            return 0.0
        normalized = self.normalize_metrics(metrics)
        raw = sum(normalized[key] * weight for key, weight in METRICS.items())
        return round(clamp(raw) * 100, 2)

    def confidence_interval(self, successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
        if n <= 0:
            return (0.0, 0.0)
        p = successes / n
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        return (round(max(0.0, center - margin), 3), round(min(1.0, center + margin), 3))

    def rank(self, accelerators: list[dict]) -> list[dict]:
        scored = [
            item | {"roi_score": self.compute_roi_score(item["metrics"], item.get("cohort_count", 0))}
            for item in accelerators
        ]
        return sorted(scored, key=lambda item: item["roi_score"], reverse=True)
