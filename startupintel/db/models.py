from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Startup(Base):
    __tablename__ = "startups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    crunchbase_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    industry: Mapped[str | None] = mapped_column(String(120), index=True)
    stage: Mapped[str | None] = mapped_column(String(40), index=True)
    hq_city: Mapped[str | None] = mapped_column(String(120))
    hq_country: Mapped[str | None] = mapped_column(String(120))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    total_funding_usd: Mapped[float | None] = mapped_column(Float)
    last_funding_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    scores: Mapped[list["StartupScore"]] = relationship(back_populates="startup")
    headcount_snapshots: Mapped[list["HeadcountSnapshot"]] = relationship(back_populates="startup")
    signal_events: Mapped[list["SignalEvent"]] = relationship(back_populates="startup")


class StartupScore(Base):
    __tablename__ = "startup_scores"
    __table_args__ = (
        UniqueConstraint("startup_id", "bot_name", "computed_at", name="uq_startup_bot_computed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    startup_id: Mapped[UUID] = mapped_column(ForeignKey("startups.id", ondelete="CASCADE"), index=True)
    bot_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    signal_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    llm_diagnosis: Mapped[str | None] = mapped_column(Text)
    similar_cases: Mapped[list] = mapped_column(JSONB, default=list)
    raw_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    startup: Mapped[Startup] = relationship(back_populates="scores")


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    firm: Mapped[str | None] = mapped_column(String(255), index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    crunchbase_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    centrality_score: Mapped[float | None] = mapped_column(Float)
    value_add_score: Mapped[float | None] = mapped_column(Float)
    betweenness: Mapped[float | None] = mapped_column(Float)
    eigenvector: Mapped[float | None] = mapped_column(Float)
    portfolio_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Accelerator(Base):
    __tablename__ = "accelerators"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    cohort_count: Mapped[int] = mapped_column(Integer, default=0)
    follow_on_rate: Mapped[float | None] = mapped_column(Float)
    median_time_to_series_a_months: Mapped[float | None] = mapped_column(Float)
    survival_rate_3yr: Mapped[float | None] = mapped_column(Float)
    unicorn_rate: Mapped[float | None] = mapped_column(Float)
    shutdown_rate: Mapped[float | None] = mapped_column(Float)
    roi_score: Mapped[float | None] = mapped_column(Float, index=True)
    industry_focus: Mapped[str | None] = mapped_column(String(120))
    stage_focus: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class TermSheetAnalysis(Base):
    __tablename__ = "termsheet_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    startup_id: Mapped[UUID | None] = mapped_column(ForeignKey("startups.id", ondelete="SET NULL"))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    founder_friendliness_score: Mapped[float] = mapped_column(Float, nullable=False)
    red_flags: Mapped[list] = mapped_column(JSONB, default=list)
    clause_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    market_benchmark: Mapped[dict] = mapped_column(JSONB, default=dict)
    llm_diagnosis: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HeadcountSnapshot(Base):
    __tablename__ = "headcount_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    startup_id: Mapped[UUID] = mapped_column(ForeignKey("startups.id", ondelete="CASCADE"), index=True)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)

    startup: Mapped[Startup] = relationship(back_populates="headcount_snapshots")


class SignalEvent(Base):
    __tablename__ = "signal_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    startup_id: Mapped[UUID] = mapped_column(ForeignKey("startups.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    emitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    startup: Mapped[Startup] = relationship(back_populates="signal_events")



class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(255))
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="analyst", index=True)  # admin, analyst, viewer
    is_active: Mapped[bool] = mapped_column(default=True)
    email_verified: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="users")
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    device_info: Mapped[str | None] = mapped_column(String(255))  # User agent, IP, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None or self.expires_at < utcnow()


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)  # First 8 chars for identification
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    scopes: Mapped[list] = mapped_column(JSONB, default=list)  # ["read", "write", "admin"]
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="api_keys")
    user: Mapped[User | None] = relationship(back_populates="api_keys")

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < utcnow():
            return False
        return True


