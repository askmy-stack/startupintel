"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create startups table
    op.create_table(
        "startups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("domain", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("crunchbase_id", sa.String(255), unique=True),
        sa.Column("founded_year", sa.Integer),
        sa.Column("industry", sa.String(120), index=True),
        sa.Column("stage", sa.String(40), index=True),
        sa.Column("hq_city", sa.String(120)),
        sa.Column("hq_country", sa.String(120)),
        sa.Column("employee_count", sa.Integer),
        sa.Column("total_funding_usd", sa.Float),
        sa.Column("last_funding_date", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create startup_scores table
    op.create_table(
        "startup_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("startup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bot_name", sa.String(40), nullable=False, index=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("signal_breakdown", postgresql.JSONB, default={}),
        sa.Column("llm_diagnosis", sa.Text),
        sa.Column("similar_cases", postgresql.JSONB, default=[]),
        sa.Column("raw_signals", postgresql.JSONB, default={}),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.UniqueConstraint("startup_id", "bot_name", "computed_at", name="uq_startup_bot_computed_at"),
    )

    # Create investors table
    op.create_table(
        "investors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("firm", sa.String(255), index=True),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("crunchbase_id", sa.String(255), unique=True),
        sa.Column("centrality_score", sa.Float),
        sa.Column("value_add_score", sa.Float),
        sa.Column("betweenness", sa.Float),
        sa.Column("eigenvector", sa.Float),
        sa.Column("portfolio_count", sa.Integer),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create accelerators table
    op.create_table(
        "accelerators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("cohort_count", sa.Integer, default=0),
        sa.Column("follow_on_rate", sa.Float),
        sa.Column("median_time_to_series_a_months", sa.Float),
        sa.Column("survival_rate_3yr", sa.Float),
        sa.Column("unicorn_rate", sa.Float),
        sa.Column("shutdown_rate", sa.Float),
        sa.Column("roi_score", sa.Float, index=True),
        sa.Column("industry_focus", sa.String(120)),
        sa.Column("stage_focus", sa.String(80)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create termsheet_analyses table
    op.create_table(
        "termsheet_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("startup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("startups.id", ondelete="SET NULL")),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("founder_friendliness_score", sa.Float, nullable=False),
        sa.Column("red_flags", postgresql.JSONB, default=[]),
        sa.Column("clause_scores", postgresql.JSONB, default={}),
        sa.Column("market_benchmark", postgresql.JSONB, default={}),
        sa.Column("llm_diagnosis", sa.Text),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create headcount_snapshots table
    op.create_table(
        "headcount_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("startup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("headcount", sa.Integer, nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source", sa.String(80), nullable=False),
    )

    # Create signal_events table
    op.create_table(
        "signal_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("startup_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(120), nullable=False, index=True),
        sa.Column("payload", postgresql.JSONB, default={}),
        sa.Column("emitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Create indexes
    op.create_index("ix_startup_scores_computed", "startup_scores", ["computed_at"])
    op.create_index("ix_signal_events_emitted", "signal_events", ["emitted_at"])


def downgrade() -> None:
    op.drop_table("signal_events")
    op.drop_table("headcount_snapshots")
    op.drop_table("termsheet_analyses")
    op.drop_table("accelerators")
    op.drop_table("investors")
    op.drop_table("startup_scores")
    op.drop_table("startups")
