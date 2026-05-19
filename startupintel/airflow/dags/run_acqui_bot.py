"""Airflow DAG for AcquiBot - Acqui-hire prediction."""

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


def run_acqui_bot_batch(**context) -> dict:
    """Run AcquiBot for all active startups."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run_batch():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.models import Startup
        from startupintel.db.redis import get_redis
        from startupintel.db.neo4j import get_neo4j_driver
        from startupintel.llm.client import get_llm_client
        from startupintel.rag.retriever import get_retriever
        from startupintel.bots.acqui_bot import AcquiBot
        from sqlalchemy import select

        db = AsyncSessionLocal()
        redis = get_redis()
        neo4j = get_neo4j_driver()
        llm = get_llm_client()
        rag = get_retriever()

        try:
            result = await db.execute(select(Startup.id))
            startup_ids = [row[0] for row in result.all()]

            bot = AcquiBot(db, neo4j, redis, rag, llm)
            results = []

            for startup_id in startup_ids[:10]:
                try:
                    result = await bot.run(startup_id)
                    results.append({
                        "startup_id": str(result.startup_id),
                        "acqui_probability": result.score,
                        "likely_acquirers": result.signal_breakdown.get("likely_acquirers", []),
                        "status": "completed",
                    })
                except Exception as e:
                    results.append({"startup_id": str(startup_id), "error": str(e)})

            return {"processed": len(results), "results": results}
        finally:
            await db.close()

    return asyncio.run(_run_batch())


with DAG(
    "acqui_bot_weekly",
    default_args=default_args,
    description="Run AcquiBot weekly for acqui-hire prediction",
    schedule_interval="0 12 * * 4",  # Weekly on Thursday at 12 PM
    start_date=days_ago(1),
    catchup=False,
    tags=["bots", "acqui", "acquisition"],
) as dag:

    run_batch = PythonOperator(
        task_id="run_acqui_bot_batch",
        python_callable=run_acqui_bot_batch,
    )

    run_batch
