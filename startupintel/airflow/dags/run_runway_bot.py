"""Airflow DAG for RunwayBot - Financial stress detection."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "startupintel",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def run_runway_bot_for_startup(startup_id: str, **context) -> dict:
    """Run RunwayBot for a single startup."""
    import os
    import sys

    # Add project to path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run():
        from startupintel.config import get_settings
        from startupintel.db.postgres import AsyncSessionLocal, engine
        from startupintel.db.redis import get_redis
        from startupintel.db.neo4j import get_neo4j_driver
        from startupintel.llm.client import get_llm_client
        from startupintel.rag.retriever import get_retriever
        from startupintel.bots.runway_bot import RunwayBot
        from uuid import UUID

        settings = get_settings()
        db = AsyncSessionLocal()
        redis = get_redis()
        neo4j = get_neo4j_driver()
        llm = get_llm_client()
        rag = get_retriever()

        try:
            bot = RunwayBot(db, neo4j, redis, rag, llm)
            result = await bot.run(UUID(startup_id))
            return {
                "startup_id": str(result.startup_id),
                "score": result.score,
                "status": "completed",
            }
        finally:
            await db.close()

    return asyncio.run(_run())


def run_runway_bot_batch(**context) -> dict:
    """Run RunwayBot for all active startups."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run_batch():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.models import Startup
        from sqlalchemy import select

        db = AsyncSessionLocal()
        try:
            result = await db.execute(select(Startup.id))
            startup_ids = [str(row[0]) for row in result.all()]

            results = []
            for startup_id in startup_ids[:10]:  # Limit batch size
                try:
                    result = run_runway_bot_for_startup(startup_id)
                    results.append(result)
                except Exception as e:
                    results.append({"startup_id": startup_id, "error": str(e)})

            return {"processed": len(results), "results": results}
        finally:
            await db.close()

    return asyncio.run(_run_batch())


with DAG(
    "runway_bot_daily",
    default_args=default_args,
    description="Run RunwayBot daily to detect financial stress",
    schedule_interval="0 6 * * *",  # Daily at 6 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["bots", "runway", "stress"],
) as dag:

    run_batch = PythonOperator(
        task_id="run_runway_bot_batch",
        python_callable=run_runway_bot_batch,
    )

    run_batch
