"""Airflow DAG for InvestorBot - Investor network analysis."""

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


def run_investor_bot_analysis(**context) -> dict:
    """Run InvestorBot for all investors."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.models import Investor
        from startupintel.db.redis import get_redis
        from startupintel.db.neo4j import get_neo4j_driver
        from startupintel.llm.client import get_llm_client
        from startupintel.rag.retriever import get_retriever
        from startupintel.bots.investor_bot import InvestorBot
        from sqlalchemy import select

        db = AsyncSessionLocal()
        redis = get_redis()
        neo4j = get_neo4j_driver()
        llm = get_llm_client()
        rag = get_retriever()

        try:
            result = await db.execute(select(Investor.id))
            investor_ids = [row[0] for row in result.all()]

            bot = InvestorBot(db, neo4j, redis, rag, llm)
            results = []

            for investor_id in investor_ids:
                try:
                    result = await bot.run(investor_id)
                    results.append({
                        "investor_id": str(result.startup_id),
                        "centrality_score": result.score,
                        "status": "completed",
                    })
                except Exception as e:
                    results.append({"investor_id": str(investor_id), "error": str(e)})

            return {"processed": len(results), "results": results}
        finally:
            await db.close()

    return asyncio.run(_run())


with DAG(
    "investor_bot_daily",
    default_args=default_args,
    description="Run InvestorBot daily for network centrality analysis",
    schedule_interval="0 11 * * *",  # Daily at 11 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["bots", "investor", "network"],
) as dag:

    run_analysis = PythonOperator(
        task_id="run_investor_bot_analysis",
        python_callable=run_investor_bot_analysis,
    )

    run_analysis
