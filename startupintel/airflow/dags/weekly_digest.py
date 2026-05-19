"""Airflow DAG for weekly digest generation."""

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


def generate_weekly_digest(**context) -> dict:
    """Generate weekly digest of all bot scores and insights."""
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    async def _generate():
        from startupintel.db.postgres import AsyncSessionLocal
        from startupintel.db.models import StartupScore, Startup
        from startupintel.llm.client import get_llm_client
        from sqlalchemy import select, func, desc
        from datetime import datetime, timedelta

        db = AsyncSessionLocal()
        llm = get_llm_client()

        try:
            # Get scores from the last 7 days
            one_week_ago = datetime.utcnow() - timedelta(days=7)

            result = await db.execute(
                select(StartupScore, Startup.name)
                .join(Startup, StartupScore.startup_id == Startup.id)
                .where(StartupScore.computed_at >= one_week_ago)
                .order_by(desc(StartupScore.score))
                .limit(50)
            )

            scores = result.all()

            # Group by bot
            by_bot = {}
            for score, startup_name in scores:
                if score.bot_name not in by_bot:
                    by_bot[score.bot_name] = []
                by_bot[score.bot_name].append({
                    "startup": startup_name,
                    "score": score.score,
                    "diagnosis": score.llm_diagnosis,
                })

            # Generate summary with LLM
            digest_data = {
                "generated_at": datetime.utcnow().isoformat(),
                "period": "last_7_days",
                "total_scores": len(scores),
                "by_bot": by_bot,
            }

            # Generate natural language summary
            prompt = f"""Generate a weekly startup intelligence digest based on this data:

{str(digest_data)[:2000]}

Create a concise executive summary highlighting:
1. Most stressed startups (RunwayBot high scores)
2. Biggest PMF improvements
3. Notable pivot signals
4. Top acqui-hire candidates
5. Key term sheet red flags

Keep it under 300 words."""

            summary = await llm.complete(prompt, temperature=0.7)

            digest = {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": summary,
                "total_scores": len(scores),
                "bots_covered": list(by_bot.keys()),
                "raw_data": digest_data,
            }

            return digest
        finally:
            await db.close()

    return asyncio.run(_generate())


with DAG(
    "weekly_digest",
    default_args=default_args,
    description="Generate weekly startup intelligence digest",
    schedule_interval="0 9 * * 5",  # Every Friday at 9 AM
    start_date=days_ago(1),
    catchup=False,
    tags=["digest", "weekly", "intelligence"],
) as dag:

    generate_digest = PythonOperator(
        task_id="generate_weekly_digest",
        python_callable=generate_weekly_digest,
    )

    generate_digest
