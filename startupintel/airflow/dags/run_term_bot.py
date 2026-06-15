"""Airflow DAG for TermBot - Term sheet analysis."""

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


def run_term_bot_analysis(**context) -> dict:
    """Run TermBot for pending term sheet analyses."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _run():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.redis import get_redis
        from startupintel.db.neo4j import get_neo4j_driver
        from startupintel.llm.client import get_llm_client
        from startupintel.rag.retriever import get_retriever
        from startupintel.bots.term_bot import TermBot

        db = AsyncSessionLocal()
        redis = get_redis()
        neo4j = get_neo4j_driver()
        llm = get_llm_client()
        rag = get_retriever()

        try:
            bot = TermBot(db, neo4j, redis, rag, llm)

            # Sample term sheet text for analysis
            sample_termsheet = """
            TERM SHEET FOR SERIES A FINANCING

            Pre-Money Valuation: $10,000,000
            Investment Amount: $3,000,000
            Liquidation Preference: 1x non-participating
            Anti-Dilution: Broad-based weighted average
            Board Seats: 1 investor seat, 2 common seats
            Vesting: 4-year vesting with 1-year cliff
            Drag-Along: Standard provisions
            No-Shop: 30 days
            """

            result = await bot.analyze_termsheet(sample_termsheet)
            return {
                "founder_friendliness": result.founder_friendliness_score,
                "red_flags": result.red_flags,
                "status": "completed",
            }
        finally:
            await db.close()

    return asyncio.run(_run())


with DAG(
    "term_bot_daily",
    default_args=default_args,
    description="Run TermBot for term sheet analysis",
    schedule_interval="0 8 * * *",  # Daily at 8 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["bots", "term", "termsheet"],
) as dag:

    run_analysis = PythonOperator(
        task_id="run_term_bot_analysis",
        python_callable=run_term_bot_analysis,
    )

    run_analysis
