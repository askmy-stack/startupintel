"""Airflow DAG for AcceleratorBot - Accelerator ROI ranking."""

from __future__ import annotations

import asyncio
from datetime import timedelta

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


def run_accelerator_bot_ranking(**context) -> dict:
    """Run AcceleratorBot to rank all accelerators."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.models import Accelerator
        from startupintel.db.redis import get_redis
        from startupintel.db.neo4j import get_neo4j_driver
        from startupintel.llm.client import get_llm_client
        from startupintel.rag.retriever import get_retriever
        from startupintel.bots.accelerator_bot import AcceleratorBot
        from sqlalchemy import select

        db = AsyncSessionLocal()
        redis = get_redis()
        neo4j = get_neo4j_driver()
        llm = get_llm_client()
        rag = get_retriever()

        try:
            result = await db.execute(select(Accelerator.id))
            accelerator_ids = [row[0] for row in result.all()]

            bot = AcceleratorBot(db, neo4j, redis, rag, llm)
            results = []

            for accel_id in accelerator_ids:
                try:
                    result = await bot.run(accel_id)
                    results.append({
                        "accelerator_id": str(result.startup_id),
                        "roi_score": result.score,
                        "status": "completed",
                    })
                except Exception as e:
                    results.append({"accelerator_id": str(accel_id), "error": str(e)})

            return {"processed": len(results), "results": results}
        finally:
            await db.close()

    return asyncio.run(_run())


with DAG(
    "accelerator_bot_weekly",
    default_args=default_args,
    description="Run AcceleratorBot weekly for ROI ranking",
    schedule_interval="0 10 * * 3",  # Weekly on Wednesday at 10 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["bots", "accelerator", "ranking"],
) as dag:

    run_ranking = PythonOperator(
        task_id="run_accelerator_bot_ranking",
        python_callable=run_accelerator_bot_ranking,
    )

    run_ranking
