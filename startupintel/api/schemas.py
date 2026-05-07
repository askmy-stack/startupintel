from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SimilarCase(BaseModel):
    name: str
    score: float
    metadata: dict = Field(default_factory=dict)


class StartupSummary(BaseModel):
    id: UUID
    name: str
    domain: str
    industry: str | None = None
    stage: str | None = None
    employee_count: int | None = None
    total_funding_usd: float | None = None


class RunwayBotOutput(BaseModel):
    startup_id: UUID
    score: float
    risk_level: str
    signal_breakdown: dict[str, float]
    headcount_delta_pct: float
    job_posting_delta_pct: float
    founder_sentiment: float
    domain_expiry_days: int
    days_since_funding: int
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    llm_diagnosis: str
    computed_at: datetime


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "startupintel-api"

