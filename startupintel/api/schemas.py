"""Pydantic schemas for API request/response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ========== Common Models ==========

class SimilarCase(BaseModel):
    """Similar historical case from RAG search."""
    name: str
    score: float
    metadata: dict = Field(default_factory=dict)


class SignalBreakdown(BaseModel):
    """Breakdown of signals contributing to a score."""
    headcount: float | None = None
    job_postings: float | None = None
    sentiment: float | None = None
    domain_renewal: float | None = None
    funding_recency: float | None = None


# ========== Startup Models ==========

class StartupBase(BaseModel):
    """Base startup model."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    crunchbase_id: str | None = None
    founded_year: int | None = None
    industry: str | None = None
    stage: str | None = Field(None, pattern="^(seed|series_a|series_b|growth)$")
    hq_city: str | None = None
    hq_country: str | None = None
    employee_count: int | None = Field(None, ge=0)
    total_funding_usd: float | None = Field(None, ge=0)
    last_funding_date: datetime | None = None


class StartupCreate(StartupBase):
    """Request model for creating a startup."""
    pass


class StartupUpdate(BaseModel):
    """Request model for updating a startup."""
    name: str | None = Field(None, min_length=1, max_length=255)
    domain: str | None = Field(None, min_length=1, max_length=255)
    founded_year: int | None = None
    industry: str | None = None
    stage: str | None = Field(None, pattern="^(seed|series_a|series_b|growth)$")
    hq_city: str | None = None
    hq_country: str | None = None
    employee_count: int | None = Field(None, ge=0)
    total_funding_usd: float | None = Field(None, ge=0)
    last_funding_date: datetime | None = None


class StartupResponse(StartupBase):
    """Response model for startup."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class StartupSummary(BaseModel):
    """Summary of a startup."""
    id: UUID
    name: str
    domain: str
    industry: str | None = None
    stage: str | None = None
    employee_count: int | None = None
    total_funding_usd: float | None = None


class StartupListResponse(BaseModel):
    """Response model for listing startups."""
    items: list[StartupSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ========== Investor Models ==========

class InvestorBase(BaseModel):
    """Base investor model."""
    name: str = Field(..., min_length=1, max_length=255)
    firm: str | None = None
    linkedin_url: str | None = None
    crunchbase_id: str | None = None


class InvestorCreate(InvestorBase):
    """Request model for creating an investor."""
    pass


class InvestorResponse(InvestorBase):
    """Response model for investor."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    centrality_score: float | None = None
    value_add_score: float | None = None
    betweenness: float | None = None
    eigenvector: float | None = None
    portfolio_count: int | None = None
    updated_at: datetime


class InvestorListResponse(BaseModel):
    """Response model for listing investors."""
    items: list[InvestorResponse]
    total: int


# ========== Accelerator Models ==========

class AcceleratorBase(BaseModel):
    """Base accelerator model."""
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    cohort_count: int = Field(default=0, ge=0)
    industry_focus: str | None = None
    stage_focus: str | None = None


class AcceleratorCreate(AcceleratorBase):
    """Request model for creating an accelerator."""
    pass


class AcceleratorResponse(AcceleratorBase):
    """Response model for accelerator."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    follow_on_rate: float | None = None
    median_time_to_series_a_months: float | None = None
    survival_rate_3yr: float | None = None
    unicorn_rate: float | None = None
    shutdown_rate: float | None = None
    roi_score: float | None = None
    updated_at: datetime


class AcceleratorListResponse(BaseModel):
    """Response model for listing accelerators."""
    items: list[AcceleratorResponse]
    total: int


# ========== Score Models ==========

class BotScoreResponse(BaseModel):
    """Response model for a bot score."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    startup_id: UUID
    bot_name: str
    score: float
    signal_breakdown: dict
    llm_diagnosis: str | None
    similar_cases: list
    raw_signals: dict
    computed_at: datetime


class BotScoreListResponse(BaseModel):
    """Response model for listing bot scores."""
    items: list[BotScoreResponse]
    total: int


class BotRunRequest(BaseModel):
    """Request model for running a bot."""
    startup_id: UUID
    force_refresh: bool = False


class BotRunResponse(BaseModel):
    """Response model for running a bot."""
    startup_id: UUID
    bot_name: str
    score: float
    status: str
    computed_at: datetime


# ========== RunwayBot Models ==========

class RunwayBotOutput(BaseModel):
    """Output from RunwayBot analysis."""
    startup_id: UUID
    score: float
    risk_level: str
    signal_breakdown: dict[str, float]
    headcount_delta_pct: float
    job_posting_delta_pct: float
    founder_sentiment: float
    domain_expiry_days: float
    days_since_funding: float
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    llm_diagnosis: str
    computed_at: datetime


# ========== ObituaryBot Models ==========

class ObituaryBotOutput(BaseModel):
    """Output from ObituaryBot analysis."""
    startup_id: UUID
    score: float
    risk_level: str
    top_failure_pattern: str
    pattern_confidence: float
    similar_failures: list[SimilarCase]
    failure_taxonomy_breakdown: dict[str, int]
    llm_diagnosis: str
    computed_at: datetime


# ========== PMFBot Models ==========

class PMFBotOutput(BaseModel):
    """Output from PMFBot analysis."""
    startup_id: UUID
    score: float
    pmf_status: str
    strongest_signal: str
    weakest_signal: str
    changepoint_detected: bool
    changepoint_date: datetime | None
    signal_breakdown: dict[str, float]
    similar_cases: list[SimilarCase]
    llm_diagnosis: str
    computed_at: datetime


# ========== PivotBot Models ==========

class PivotEvent(BaseModel):
    """A detected pivot event."""
    date: datetime
    pivot_type: str
    confidence: float
    evidence_summary: str


class PivotBotOutput(BaseModel):
    """Output from PivotBot analysis."""
    startup_id: UUID
    score: float
    pivot_count: int
    primary_pivot_type: str | None
    pivot_events: list[PivotEvent]
    avg_confidence: float
    llm_diagnosis: str
    computed_at: datetime


# ========== AcquiBot Models ==========

class LikelyAcquirer(BaseModel):
    """A likely acquirer with fit score."""
    acquirer_id: UUID
    name: str
    domain: str
    fit_score: float
    tech_overlap: float
    team_fit: float
    network_overlap: float
    rationale: str


class AcquiBotOutput(BaseModel):
    """Output from AcquiBot analysis."""
    startup_id: UUID
    score: float
    probability: float
    group_scores: dict[str, float]
    feature_importances: dict[str, float]
    likely_acquirers: list[LikelyAcquirer]
    llm_diagnosis: str
    computed_at: datetime


# ========== InvestorBot Models ==========

class InvestorBotOutput(BaseModel):
    """Output from InvestorBot analysis."""
    startup_id: UUID
    score: float
    network_metrics: dict[str, float]
    diversity_score: float
    co_investor_graph: dict[str, list[str]]
    llm_diagnosis: str
    computed_at: datetime


# ========== AcceleratorBot Models ==========

class AcceleratorBotOutput(BaseModel):
    """Output from AcceleratorBot analysis."""
    accelerator_id: UUID
    name: str
    roi_score: float
    global_rank: int
    industry_rank: int
    geo_rank: int
    normalized_metrics: dict[str, float]
    confidence_interval: tuple[float, float]
    peer_comparison: list[dict]
    computed_at: datetime


# ========== TermBot Models ==========

class ClauseAnalysis(BaseModel):
    """Analysis of a specific term sheet clause."""
    detected_value: str
    is_market_standard: bool
    risk_level: str
    explanation: str
    founder_impact: str
    weight: float
    score: float


class TermBotOutput(BaseModel):
    """Output from TermBot analysis."""
    analysis_id: UUID
    startup_id: UUID | None
    founder_friendliness_score: float
    market_benchmark_score: float
    red_flags: list[str]
    yellow_flags: list[str]
    clause_scores: dict[str, ClauseAnalysis]
    llm_diagnosis: str
    analyzed_at: datetime


# ========== Search Models ==========

class StartupSearchRequest(BaseModel):
    """Request model for searching startups."""
    query: str | None = None
    industry: str | None = None
    stage: str | None = None
    min_funding: float | None = None
    max_funding: float | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class StartupSearchResponse(BaseModel):
    """Response model for startup search."""
    items: list[StartupSummary]
    total: int
    page: int
    page_size: int


# ========== Health Model ==========

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "startupintel-api"
    version: str = "0.1.0"


# ========== Error Models ==========

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

