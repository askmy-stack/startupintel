"""Database seeding script for StartupIntel."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from startupintel.db.models import (
    Base, Startup, Investor, Accelerator,
    HeadcountSnapshot, StartupScore,
)
from startupintel.db.postgres import AsyncSessionLocal, engine


# ========== Sample Startups ==========

SAMPLE_STARTUPS = [
    Startup(
        id=uuid4(),
        name="Acme Analytics",
        domain="acmeanalytics.io",
        founded_year=2021,
        industry="saas",
        stage="seed",
        hq_city="San Francisco",
        hq_country="USA",
        employee_count=42,
        total_funding_usd=4_200_000,
        last_funding_date=datetime.utcnow() - timedelta(days=400),
    ),
    Startup(
        id=uuid4(),
        name="Northstar Robotics",
        domain="northstarrobotics.com",
        founded_year=2020,
        industry="robotics",
        stage="series_a",
        hq_city="Boston",
        hq_country="USA",
        employee_count=88,
        total_funding_usd=18_000_000,
        last_funding_date=datetime.utcnow() - timedelta(days=200),
    ),
    Startup(
        id=uuid4(),
        name="Quantum Health",
        domain="quantumhealth.io",
        founded_year=2022,
        industry="healthcare",
        stage="seed",
        hq_city="New York",
        hq_country="USA",
        employee_count=25,
        total_funding_usd=2_500_000,
        last_funding_date=datetime.utcnow() - timedelta(days=150),
    ),
    Startup(
        id=uuid4(),
        name="GreenLeaf AI",
        domain="greenleaf.ai",
        founded_year=2021,
        industry="ai_ml",
        stage="series_a",
        hq_city="Seattle",
        hq_country="USA",
        employee_count=65,
        total_funding_usd=12_000_000,
        last_funding_date=datetime.utcnow() - timedelta(days=300),
    ),
    Startup(
        id=uuid4(),
        name="FintechFlow",
        domain="fintechflow.com",
        founded_year=2019,
        industry="fintech",
        stage="series_b",
        hq_city="London",
        hq_country="UK",
        employee_count=120,
        total_funding_usd=45_000_000,
        last_funding_date=datetime.utcnow() - timedelta(days=180),
    ),
    Startup(
        id=uuid4(),
        name="EdVenture",
        domain="edventure.io",
        founded_year=2020,
        industry="education",
        stage="series_a",
        hq_city="Berlin",
        hq_country="Germany",
        employee_count=55,
        total_funding_usd=8_000_000,
        last_funding_date=datetime.utcnow() - timedelta(days=250),
    ),
    Startup(
        id=uuid4(),
        name="CryptoVault",
        domain="cryptovault.io",
        founded_year=2021,
        industry="crypto",
        stage="seed",
        hq_city="Singapore",
        hq_country="Singapore",
        employee_count=18,
        total_funding_usd=1_800_000,
        last_funding_date=datetime.utcnow() - timedelta(days=90),
    ),
    Startup(
        id=uuid4(),
        name="DevTools Pro",
        domain="devtools.pro",
        founded_year=2019,
        industry="developer_tools",
        stage="series_b",
        hq_city="Austin",
        hq_country="USA",
        employee_count=95,
        total_funding_usd=28_000_000,
        last_funding_date=datetime.utcnow() - timedelta(days=120),
    ),
]


# ========== Sample Investors ==========

SAMPLE_INVESTORS = [
    Investor(
        id=uuid4(),
        name="Sarah Chen",
        firm="Accel Partners",
        centrality_score=0.85,
        value_add_score=0.78,
        betweenness=0.72,
        eigenvector=0.80,
        portfolio_count=42,
    ),
    Investor(
        id=uuid4(),
        name="Michael Ross",
        firm="Sequoia Capital",
        centrality_score=0.92,
        value_add_score=0.88,
        betweenness=0.85,
        eigenvector=0.91,
        portfolio_count=65,
    ),
    Investor(
        id=uuid4(),
        name="Emily Watson",
        firm="Andreessen Horowitz",
        centrality_score=0.88,
        value_add_score=0.90,
        betweenness=0.78,
        eigenvector=0.87,
        portfolio_count=58,
    ),
    Investor(
        id=uuid4(),
        name="David Kim",
        firm="Lightspeed Venture Partners",
        centrality_score=0.75,
        value_add_score=0.72,
        betweenness=0.68,
        eigenvector=0.74,
        portfolio_count=35,
    ),
]


# ========== Sample Accelerators ==========

SAMPLE_ACCELERATORS = [
    Accelerator(
        id=uuid4(),
        name="Y Combinator",
        location="Mountain View, CA",
        cohort_count=300,
        follow_on_rate=0.72,
        median_time_to_series_a_months=8.5,
        survival_rate_3yr=0.85,
        unicorn_rate=0.12,
        shutdown_rate=0.10,
        roi_score=95.0,
        industry_focus="general",
        stage_focus="seed",
    ),
    Accelerator(
        id=uuid4(),
        name="Techstars",
        location="Boulder, CO",
        cohort_count=250,
        follow_on_rate=0.65,
        median_time_to_series_a_months=10.2,
        survival_rate_3yr=0.78,
        unicorn_rate=0.08,
        shutdown_rate=0.15,
        roi_score=82.0,
        industry_focus="general",
        stage_focus="seed",
    ),
    Accelerator(
        id=uuid4(),
        name="500 Startups",
        location="San Francisco, CA",
        cohort_count=280,
        follow_on_rate=0.58,
        median_time_to_series_a_months=11.5,
        survival_rate_3yr=0.72,
        unicorn_rate=0.06,
        shutdown_rate=0.18,
        roi_score=75.0,
        industry_focus="general",
        stage_focus="seed",
    ),
    Accelerator(
        id=uuid4(),
        name="Alchemist Accelerator",
        location="San Francisco, CA",
        cohort_count=80,
        follow_on_rate=0.68,
        median_time_to_series_a_months=9.8,
        survival_rate_3yr=0.80,
        unicorn_rate=0.05,
        shutdown_rate=0.12,
        roi_score=78.0,
        industry_focus="enterprise",
        stage_focus="seed",
    ),
]


def generate_headcount_snapshots(startup_id, start_count: int, days: int = 60) -> list:
    """Generate headcount snapshots showing growth/decline patterns."""
    snapshots = []
    current_count = start_count

    for i in range(days // 7):  # Weekly snapshots
        # Random fluctuation (-5% to +10%)
        change = current_count * (0.95 + (i % 10) / 100)
        current_count = int(change)

        snapshots.append(HeadcountSnapshot(
            id=uuid4(),
            startup_id=startup_id,
            headcount=current_count,
            snapshot_date=datetime.utcnow() - timedelta(days=days - i * 7),
            source="linkedin",
        ))

    return snapshots


async def seed_database() -> None:
    """Seed the database with sample data."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Add startups
        for startup in SAMPLE_STARTUPS:
            session.add(startup)
        await session.flush()

        # Add investors
        for investor in SAMPLE_INVESTORS:
            session.add(investor)

        # Add accelerators
        for accelerator in SAMPLE_ACCELERATORS:
            session.add(accelerator)

        # Generate headcount snapshots for each startup
        for startup in SAMPLE_STARTUPS:
            snapshots = generate_headcount_snapshots(startup.id, startup.employee_count or 10)
            for snapshot in snapshots:
                session.add(snapshot)

        # Add some sample scores
        for startup in SAMPLE_STARTUPS[:4]:
            score = StartupScore(
                id=uuid4(),
                startup_id=startup.id,
                bot_name="runway",
                score=65.0 + (startup.employee_count or 0) % 30,
                signal_breakdown={
                    "headcount": 0.7,
                    "job_postings": 0.6,
                    "sentiment": 0.5,
                    "domain_renewal": 0.9,
                    "funding_recency": 0.4,
                },
                llm_diagnosis=f"Runway analysis for {startup.name}: Moderate stress signals detected.",
                similar_cases=[],
                raw_signals={},
            )
            session.add(score)

        await session.commit()
        print(f"Seeded {len(SAMPLE_STARTUPS)} startups, {len(SAMPLE_INVESTORS)} investors, {len(SAMPLE_ACCELERATORS)} accelerators")


async def verify_seed() -> None:
    """Verify the seeded data."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func

        startup_count = await session.scalar(select(func.count()).select_from(Startup))
        investor_count = await session.scalar(select(func.count()).select_from(Investor))
        accelerator_count = await session.scalar(select(func.count()).select_from(Accelerator))
        headcount_count = await session.scalar(select(func.count()).select_from(HeadcountSnapshot))
        score_count = await session.scalar(select(func.count()).select_from(StartupScore))

        print("\nDatabase verification:")
        print(f"  - Startups: {startup_count}")
        print(f"  - Investors: {investor_count}")
        print(f"  - Accelerators: {accelerator_count}")
        print(f"  - Headcount snapshots: {headcount_count}")
        print(f"  - Bot scores: {score_count}")


async def main() -> None:
    """Main entry point."""
    print("Seeding StartupIntel database...")
    await seed_database()
    await verify_seed()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

