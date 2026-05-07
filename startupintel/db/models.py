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

