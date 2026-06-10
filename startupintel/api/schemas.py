from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


# ========== Startup CRUD ==========


class StartupCreate(BaseModel):
    name: str
    domain: str
    crunchbase_id: str | None = None
    founded_year: int | None = None
    industry: str | None = None
    stage: str | None = None
    hq_city: str | None = None
    hq_country: str | None = None
    employee_count: int | None = None
    total_funding_usd: float | None = None
    last_funding_date: datetime | None = None


class StartupResponse(StartupCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class StartupListResponse(BaseModel):
    items: list[StartupResponse]
    total: int


# ========== Investor CRUD ==========


class InvestorCreate(BaseModel):
    name: str
    firm: str | None = None
    linkedin_url: str | None = None
    crunchbase_id: str | None = None
    centrality_score: float | None = None
    value_add_score: float | None = None
    betweenness: float | None = None
    eigenvector: float | None = None
    portfolio_count: int | None = None


class InvestorResponse(InvestorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    updated_at: datetime


class InvestorListResponse(BaseModel):
    items: list[InvestorResponse]
    total: int


# ========== Accelerator CRUD ==========


class AcceleratorCreate(BaseModel):
    name: str
    location: str
    cohort_count: int = 0
    follow_on_rate: float | None = None
    median_time_to_series_a_months: float | None = None
    survival_rate_3yr: float | None = None
    unicorn_rate: float | None = None
    shutdown_rate: float | None = None
    roi_score: float | None = None
    industry_focus: str | None = None
    stage_focus: str | None = None


class AcceleratorResponse(AcceleratorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    updated_at: datetime


class AcceleratorListResponse(BaseModel):
    items: list[AcceleratorResponse]
    total: int


# ========== Term sheet CRUD ==========


class TermSheetCreate(BaseModel):
    startup_id: UUID | None = None
    raw_text: str
    founder_friendliness_score: float
    red_flags: list = Field(default_factory=list)
    clause_scores: dict = Field(default_factory=dict)
    market_benchmark: dict = Field(default_factory=dict)
    llm_diagnosis: str | None = None


class TermSheetResponse(TermSheetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analyzed_at: datetime


class TermSheetListResponse(BaseModel):
    items: list[TermSheetResponse]
    total: int


# ========== Auth schemas ==========


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str
    is_active: bool
    email_verified: bool
    organization_id: UUID
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

