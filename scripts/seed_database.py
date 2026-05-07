from __future__ import annotations

import asyncio

from startupintel.db.models import Base, Startup
from startupintel.db.postgres import AsyncSessionLocal, engine


SAMPLE_STARTUPS = [
    Startup(
        name="Acme Analytics",
        domain="acmeanalytics.example",
        founded_year=2021,
        industry="saas",
        stage="seed",
        employee_count=42,
        total_funding_usd=4_200_000,
    ),
    Startup(
        name="Northstar Robotics",
        domain="northstarrobotics.example",
        founded_year=2020,
        industry="robotics",
        stage="series_a",
        employee_count=88,
        total_funding_usd=18_000_000,
    ),
]


async def main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        session.add_all(SAMPLE_STARTUPS)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())

