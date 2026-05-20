# BOT BUILD PLANS — StartupIntel

**This document extends CLAUDE.md with granular day-by-day execution plans for each of the 8 bots.**

Read CLAUDE.md first. Then use this document as the implementation roadmap.

---

## Overview

Each bot gets 3–7 days of coding. Total: 10 weeks from Day 1 infrastructure to Day 70 deployment.

**Format per bot:**
- Day-by-day breakdown
- Exact functions to write
- Exact test cases
- Code patterns + pseudocode
- Success criteria
- Dependency map

---

## Bot 1 — RunwayBot (Days 8–14)

**Reference:** CLAUDE.md § Bot 1 — RunwayBot (lines 409–473)

### Day 8 — Ingestion Connectors

**Objective:** Build the 5 data source connectors RunwayBot depends on.

**Files to create:**

**1. `startupintel/ingestion/linkedin.py`**
```python
# Class: LinkedInHeadcountConnector(BaseConnector)
# Method: async get_headcount(linkedin_url: str) -> int
# Method: async get_headcount_snapshots(startup_id: UUID, days_back: int = 90) -> list[HeadcountSnapshot]
# Library: Playwright (headless browser automation)
# Returns: Current headcount + historical snapshots from LinkedIn company page

# Logic:
# 1. Navigate to linkedin_url/about/employees
# 2. Extract current headcount from "X employees" text
# 3. Store snapshot in DB with snapshot_date = now
# 4. Retrieve past snapshots (HeadcountSnapshot table) for delta calculation

# Graceful degradation:
# - LinkedIn blocks scraper? → log warning, return cached value if < 7 days old
# - Page structure changes? → try fallback selectors, then return None
```

**2. `startupintel/ingestion/job_boards.py`**
```python
# Class: JobBoardConnector(BaseConnector)
# Method: async get_job_posting_count(domain: str) -> int
# Sources: Indeed + LinkedIn job search APIs
# Returns: Number of active job postings for this company

# Logic:
# 1. Query Indeed API: search by company domain
# 2. Query LinkedIn API: search by company name
# 3. Sum both counts
# 4. Store snapshot in DB with snapshot_date = now

# Graceful degradation:
# - API rate limited? → return cached count if < 24 hours old
# - No API access? → return None (RunwayBot will compute without this signal)
```

**3. `startupintel/ingestion/twitter.py` (sentiment only)**
```python
# Class: TwitterSentimentConnector(BaseConnector)
# Method: async get_founder_sentiment(startup_id: UUID, days: int = 7) -> float
# Returns: VADER sentiment score (-1 to 1) averaged over last N days

# Logic:
# 1. Get founder Twitter handles from Startup + Founder nodes in Neo4j
# 2. Fetch recent tweets (VADER requires raw text)
# 3. Compute VADER sentiment for each tweet
# 4. Return 7-day rolling average

# Score mapping:
# -1.0 (very negative) → stress signal
# 0.0 (neutral) → baseline
# +1.0 (very positive) → no stress signal
```

**4. `startupintel/ingestion/domain_whois.py`**
```python
# Class: WHOISConnector(BaseConnector)
# Method: async get_domain_expiry_days(domain: str) -> int
# Returns: Days until domain expires

# Logic:
# 1. Query WHOIS database (python-whois library)
# 2. Parse expiry_date from response
# 3. Compute (expiry_date - today).days
# 4. Cache for 30 days (WHOIS data changes slowly)

# Graceful degradation:
# - WHOIS lookup fails? → return 365 (assume 1 year left, neutral signal)
```

**5. `startupintel/ingestion/crunchbase.py` (extend existing)**
```python
# Extend existing crunchbase.py with:
# Method: async get_funding_history(startup_id: UUID) -> list[FundingRound]
# Method: async get_days_since_last_funding(startup_id: UUID) -> int

# Use: Last funding date stored in Startup model
# Returns: Days since last documented funding round
```

**Tests to write:**

```python
# tests/test_bots/fixtures/runway_bot_fixtures.py

LINKEDIN_FIXTURE = {
    "startup_id": UUID(),
    "headcount_now": 47,
    "headcount_30d_ago": 52,
    "headcount_delta_pct": -9.6
}

JOB_POSTING_FIXTURE = {
    "startup_id": UUID(),
    "postings_now": 0,
    "postings_30d_ago": 8,
    "postings_delta_pct": -100.0
}

SENTIMENT_FIXTURE = {
    "founder_tweets_7d": [
        {"text": "Tough times but we're pushing through", "sentiment": -0.4},
        {"text": "Closing our series A!!!", "sentiment": +0.8}
    ],
    "avg_sentiment": +0.2
}

DOMAIN_FIXTURE = {
    "domain": "company.com",
    "days_until_expiry": 45
}

FUNDING_FIXTURE = {
    "last_funding_date": datetime(2024, 3, 15),
    "days_since": 53
}
```

**Success criteria:**

- [ ] All 5 connectors instantiate without error
- [ ] `await LinkedInHeadcountConnector().get_headcount()` returns int > 0 or None
- [ ] `await JobBoardConnector().get_job_posting_count()` returns int >= 0 or None
- [ ] `await TwitterSentimentConnector().get_founder_sentiment()` returns float -1 to 1
- [ ] `await WHOISConnector().get_domain_expiry_days()` returns int > 0
- [ ] Cached values return within 50ms on second call

---

### Day 9 — RunwayBot Scoring Logic

**Objective:** Implement the RunwayBot class with full scoring formula.

**File:** `startupintel/bots/runway_bot.py`

```python
from startupintel.bots.base import BaseBot, BotResult
from startupintel.scoring.normalizer import normalize_0_to_1

class RunwayBot(BaseBot):
    name = "runway_bot"
    required_signals = [
        "headcount_now", "headcount_30d_ago",
        "job_postings_now", "job_postings_30d_ago",
        "founder_sentiment_7d",
        "domain_expiry_days",
        "days_since_last_funding"
    ]

    async def fetch_signals(self, startup_id: UUID) -> dict:
        """Fetch all 5 raw signals for RunwayBot scoring."""
        startup = await self.db.get(Startup, startup_id)
        
        # Call each connector
        hc_connector = LinkedInHeadcountConnector(self.redis)
        hc_now = await hc_connector.get_headcount(startup.linkedin_url) or startup.employee_count or 1
        hc_30d = await self.db.get_headcount_snapshot(startup_id, days_ago=30) or hc_now
        
        jp_connector = JobBoardConnector()
        jp_now = await jp_connector.get_job_posting_count(startup.domain) or 0
        jp_30d = await self.db.get_job_posting_snapshot(startup_id, days_ago=30) or jp_now or 1
        
        sentiment_connector = TwitterSentimentConnector()
        sentiment = await sentiment_connector.get_founder_sentiment(startup_id, days=7) or 0.0
        
        domain_connector = WHOISConnector()
        domain_expiry = await domain_connector.get_domain_expiry_days(startup.domain) or 365
        
        days_since_funding = (datetime.utcnow() - (startup.last_funding_date or datetime.utcnow())).days
        
        return {
            "headcount_now": hc_now,
            "headcount_30d_ago": hc_30d,
            "job_postings_now": jp_now,
            "job_postings_30d_ago": jp_30d,
            "founder_sentiment_7d": sentiment,
            "domain_expiry_days": domain_expiry,
            "days_since_last_funding": days_since_funding
        }

    async def compute_score(self, signals: dict) -> dict[str, float]:
        """Compute per-signal scores 0-1, before normalization to 0-100."""
        
        # Headcount delta: -30% drop = score 1.0 (maximum stress)
        hc_delta_pct = (signals["headcount_now"] - signals["headcount_30d_ago"]) / max(signals["headcount_30d_ago"], 1) * 100
        headcount_score = normalize_0_to_1(
            value=hc_delta_pct,
            stress_condition=lambda x: -x,  # negative delta = stress
            min_stress=-30,  # -30% is max stress (1.0)
            max_safe=+5     # +5% growth is no stress (0.0)
        )
        
        # Job posting delta: -100% (from 8 to 0) = score 1.0
        if signals["job_postings_30d_ago"] > 0:
            jp_delta_pct = (signals["job_postings_now"] - signals["job_postings_30d_ago"]) / signals["job_postings_30d_ago"] * 100
        else:
            jp_delta_pct = 0
        job_score = normalize_0_to_1(
            value=jp_delta_pct,
            stress_condition=lambda x: -x,
            min_stress=-50,
            max_safe=+10
        )
        
        # Sentiment: -1.0 (very negative) = score 1.0
        sentiment_score = normalize_0_to_1(
            value=signals["founder_sentiment_7d"],
            stress_condition=lambda x: -x,  # negative sentiment = stress
            min_stress=-1.0,
            max_safe=+0.5
        )
        
        # Domain expiry: < 30 days = score 1.0 (stress: domain renewal failure signal)
        domain_score = normalize_0_to_1(
            value=signals["domain_expiry_days"],
            stress_condition=lambda x: 90 - x,  # fewer days left = stress
            min_stress=0,
            max_safe=90
        )
        
        # Funding recency: > 18 months (540 days) = score 1.0 (burning cash with no new capital)
        funding_score = normalize_0_to_1(
            value=signals["days_since_last_funding"],
            stress_condition=lambda x: x - 365,
            min_stress=0,
            max_safe=540
        )
        
        return {
            "headcount": max(0, min(1, headcount_score)),
            "job_postings": max(0, min(1, job_score)),
            "sentiment": max(0, min(1, sentiment_score)),
            "domain_renewal": max(0, min(1, domain_score)),
            "funding_recency": max(0, min(1, funding_score))
        }

    def get_weights(self) -> dict[str, float]:
        """Return signal weights from config."""
        return {
            "headcount": float(os.getenv("RUNWAY_WEIGHT_HEADCOUNT", 0.35)),
            "job_postings": float(os.getenv("RUNWAY_WEIGHT_JOB_POSTINGS", 0.25)),
            "sentiment": float(os.getenv("RUNWAY_WEIGHT_SENTIMENT", 0.20)),
            "domain_renewal": float(os.getenv("RUNWAY_WEIGHT_DOMAIN", 0.10)),
            "funding_recency": float(os.getenv("RUNWAY_WEIGHT_FUNDING_RECENCY", 0.10))
        }

    def build_rag_query(self, signals: dict) -> str:
        """Build semantic search query for RAG retrieval of similar failure cases."""
        hc_delta = signals["headcount_now"] - signals["headcount_30d_ago"]
        jp_delta = signals["job_postings_now"] - signals["job_postings_30d_ago"]
        return f"startup headcount dropped {abs(hc_delta)} employees job postings fell {abs(jp_delta)} financial stress"

    def diagnosis_prompt_template(self) -> str:
        """LLM prompt for generating diagnosis narrative."""
        return """
You are a startup analyst detecting financial distress signals.

Startup runway stress score: {score}/100
Signal breakdown:
- Headcount change (30d): {headcount_delta}% (from {hc_30d} to {hc_now} employees)
- Job posting change (30d): {job_delta}% (from {jp_30d} to {jp_now} postings)
- Founder sentiment (7d avg): {sentiment_score:.2f}/1.0
- Domain expires in: {domain_expiry_days} days
- Days since last funding: {days_since_funding} days

Most similar historical cases (from failure corpus):
{similar_cases}

Write a 3-sentence diagnosis:
1. What the signals indicate about current financial state
2. Which signal is the strongest indicator and why
3. Recommended action (monitor / investigate / alert portfolio)

Be specific. Reference the numbers. No filler. No hedging.
"""

    async def maybe_emit_event(self, result: BotResult) -> None:
        """Emit Kafka event if runway stress is high."""
        if result.score > float(os.getenv("RUNWAY_HIGH_STRESS_THRESHOLD", 65)):
            await self.events_producer.emit({
                "topic": "startup.stress.high",
                "payload": {
                    "startup_id": str(result.startup_id),
                    "score": result.score,
                    "signal_breakdown": result.signal_breakdown,
                    "computed_at": result.computed_at.isoformat()
                }
            })
```

**Helper:** `startupintel/scoring/normalizer.py`

```python
def normalize_0_to_1(value: float, stress_condition, min_stress: float, max_safe: float) -> float:
    """
    Normalize a value to 0-1 where:
    - 0 = no stress (value >= max_safe)
    - 1 = maximum stress (value <= min_stress)
    - Linear interpolation between
    """
    stress_value = stress_condition(value)
    if stress_value <= 0:
        return 0.0
    if stress_value >= (min_stress - max_safe):
        return 1.0
    return stress_value / (min_stress - max_safe)
```

**Success criteria:**

- [ ] `RunwayBot().compute_score()` returns dict with 5 float scores in [0, 1]
- [ ] Weighted sum of scores produces final score in [0, 100]
- [ ] Fixture test: low-stress startup → score < 30
- [ ] Fixture test: high-stress startup → score > 70
- [ ] Missing signal (None) → score computed without it, not crashed
- [ ] LLM prompt template compiles (all {placeholders} present)

---

### Day 10 — API Endpoint + Database Persistence

**Objective:** Add RunwayBot to FastAPI, persist scores to Postgres.

**File:** `startupintel/api/routes/startup.py`

```python
from fastapi import APIRouter, Path
from startupintel.api.schemas import RunwayBotOutput
from startupintel.bots.runway_bot import RunwayBot

router = APIRouter(prefix="/startup", tags=["startup"])

@router.get("/{startup_id}/stress", response_model=RunwayBotOutput)
async def get_runway_stress(
    startup_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    rag: RAGRetriever = Depends(get_rag),
    llm: LLMClient = Depends(get_llm)
) -> RunwayBotOutput:
    """
    Get RunwayBot stress score for a startup.
    
    Returns: RunwayBotOutput with score, signal breakdown, diagnosis
    Cache: 1 hour TTL
    """
    bot = RunwayBot(db=db, neo4j=neo4j, redis=redis, rag_retriever=rag, llm_client=llm)
    result = await bot.run(startup_id)
    
    # Persist to Postgres
    score_record = StartupScore(
        startup_id=startup_id,
        bot_name="runway_bot",
        score=result.score,
        signal_breakdown=result.signal_breakdown,
        llm_diagnosis=result.llm_diagnosis,
        similar_cases=[s.dict() for s in result.similar_cases],
        raw_signals=result.raw_signals,
        computed_at=result.computed_at
    )
    db.add(score_record)
    await db.commit()
    
    # Write to Neo4j node
    await neo4j.run("""
        MATCH (s:Startup {id: $startup_id})
        SET s.runway_score = $score, s.runway_updated_at = $updated_at
    """, startup_id=str(startup_id), score=result.score, updated_at=result.computed_at)
    
    return RunwayBotOutput(
        startup_id=startup_id,
        score=result.score,
        risk_level=classify_risk(result.score),
        signal_breakdown=result.signal_breakdown,
        headcount_delta_pct=result.raw_signals["headcount_now"] - result.raw_signals["headcount_30d_ago"],
        job_posting_delta_pct=result.raw_signals["job_postings_now"] - result.raw_signals["job_postings_30d_ago"],
        founder_sentiment=result.raw_signals["founder_sentiment_7d"],
        domain_expiry_days=result.raw_signals["domain_expiry_days"],
        days_since_funding=result.raw_signals["days_since_last_funding"],
        similar_cases=result.similar_cases,
        llm_diagnosis=result.llm_diagnosis,
        computed_at=result.computed_at
    )

def classify_risk(score: float) -> str:
    if score < 26:
        return "low"
    elif score < 51:
        return "monitor"
    elif score < 76:
        return "elevated"
    else:
        return "high"
```

**File:** `startupintel/api/schemas.py` (add RunwayBotOutput)

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class SimilarCase(BaseModel):
    startup_name: str
    failure_cause: str
    similarity_score: float
    url: str

class RunwayBotOutput(BaseModel):
    startup_id: UUID
    score: float
    risk_level: str
    signal_breakdown: dict[str, float]
    headcount_delta_pct: float
    job_posting_delta_pct: float
    founder_sentiment: float
    domain_expiry_days: int
    days_since_funding: int
    similar_cases: List[SimilarCase]
    llm_diagnosis: str
    computed_at: datetime
```

**Success criteria:**

- [ ] `GET /startup/{id}/stress` returns 200 with RunwayBotOutput JSON
- [ ] Score persisted to `startup_scores` table in Postgres
- [ ] Score written to Startup node in Neo4j (runway_score property)
- [ ] Cache hit on second call returns response < 50ms
- [ ] Invalid startup_id returns 404

---

### Day 11 — Kafka Event Emission + Cross-Bot Trigger Setup

**Objective:** Emit `startup.stress.high` events. Set up handlers for downstream bots.

**File:** `startupintel/events/producer.py`

```python
from kafka import KafkaProducer
import json
from datetime import datetime
from loguru import logger

class EventProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
    
    async def emit_startup_stress_high(self, startup_id: str, score: float, signal_breakdown: dict) -> None:
        """Emit event when RunwayBot score > 65."""
        logger.info(f"Emitting startup.stress.high | startup={startup_id} | score={score}")
        self.producer.send("startup.stress.high", value={
            "startup_id": startup_id,
            "score": score,
            "signal_breakdown": signal_breakdown,
            "emitted_at": datetime.utcnow().isoformat()
        })
        self.producer.flush()
```

**File:** `startupintel/events/handlers.py` (first handler)

```python
from kafka import KafkaConsumer
import json
from loguru import logger
import asyncio

class EventHandler:
    def __init__(self, db, neo4j, redis, rag, llm, bootstrap_servers="localhost:9092"):
        self.db = db
        self.neo4j = neo4j
        self.redis = redis
        self.rag = rag
        self.llm = llm
        self.consumer = KafkaConsumer(
            "startup.stress.high",
            bootstrap_servers=bootstrap_servers,
            group_id="startupintel-stress-handler",
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
    
    async def handle_startup_stress_high(self) -> None:
        """Handle startup.stress.high events by triggering downstream bots."""
        for message in self.consumer:
            event = message.value
            startup_id = event["startup_id"]
            logger.info(f"Handling startup.stress.high event | startup={startup_id}")
            
            # Trigger PivotBot
            try:
                from startupintel.bots.pivot_bot import PivotBot
                pivot_bot = PivotBot(self.db, self.neo4j, self.redis, self.rag, self.llm)
                result = await pivot_bot.run(startup_id)
                logger.info(f"PivotBot completed | startup={startup_id} | pivots={result.pivot_count}")
            except Exception as e:
                logger.error(f"PivotBot failed | startup={startup_id} | error={e}")
            
            # Trigger ObituaryBot
            try:
                from startupintel.bots.obituary_bot import ObituaryBot
                obit_bot = ObituaryBot(self.db, self.neo4j, self.redis, self.rag, self.llm)
                result = await obit_bot.run(startup_id)
                logger.info(f"ObituaryBot completed | startup={startup_id} | failure_match={result.score}")
            except Exception as e:
                logger.error(f"ObituaryBot failed | startup={startup_id} | error={e}")
            
            # Trigger AcquiBot
            try:
                from startupintel.bots.acqui_bot import AcquiBot
                acqui_bot = AcquiBot(self.db, self.neo4j, self.redis, self.rag, self.llm)
                result = await acqui_bot.run(startup_id)
                logger.info(f"AcquiBot completed | startup={startup_id} | acqui_prob={result.acqui_probability}")
            except Exception as e:
                logger.error(f"AcquiBot failed | startup={startup_id} | error={e}")
            
            # All downstream bots complete → synthesizer generates unified brief
            try:
                from startupintel.llm.synthesizer import Synthesizer
                synth = Synthesizer(self.db, self.neo4j, self.llm)
                brief = await synth.generate_brief(startup_id)
                logger.info(f"Synthesizer generated brief | startup={startup_id} | brief_length={len(brief)}")
            except Exception as e:
                logger.error(f"Synthesizer failed | startup={startup_id} | error={e}")
```

**Success criteria:**

- [ ] RunwayBot with score > 65 emits `startup.stress.high` event to Kafka
- [ ] Event payload contains startup_id, score, signal_breakdown
- [ ] EventHandler listens to `startup.stress.high` topic
- [ ] PivotBot, ObituaryBot, AcquiBot triggered asynchronously (no await blocking)
- [ ] Errors in downstream bots logged but don't crash handler

---

### Day 12 — Airflow DAG Scheduling

**Objective:** Create Airflow DAG to run RunwayBot daily on all tracked startups.

**File:** `startupintel/airflow/dags/run_runway_bot.py`

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import asyncio
from sqlalchemy import select
from startupintel.db.postgres import AsyncSessionLocal
from startupintel.db.models import Startup
from startupintel.bots.runway_bot import RunwayBot
from startupintel.db.neo4j import neo4j_driver
from startupintel.db.redis import redis_client
from startupintel.rag.retriever import RAGRetriever
from startupintel.llm.client import LLMClient

default_args = {
    'owner': 'startupintel',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2)
}

dag = DAG(
    'run_runway_bot',
    default_args=default_args,
    description='Daily RunwayBot execution',
    schedule_interval='0 6 * * *',  # 6am UTC daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['runway_bot', 'daily']
)

def ingest_linkedin_headcount():
    """Task 1: Refresh LinkedIn headcount snapshots."""
    async def _ingest():
        from startupintel.ingestion.linkedin import LinkedInHeadcountConnector
        db = AsyncSessionLocal()
        connector = LinkedInHeadcountConnector(redis_client)
        
        # Get all tracked startups
        result = await db.execute(select(Startup).limit(500))
        startups = result.scalars().all()
        
        success_count = 0
        for startup in startups:
            if not startup.linkedin_url:
                continue
            try:
                hc = await connector.get_headcount(startup.linkedin_url)
                if hc:
                    success_count += 1
            except Exception as e:
                logger.warning(f"LinkedIn ingest failed | startup={startup.id} | error={e}")
        
        logger.info(f"LinkedIn ingest complete | total={len(startups)} | success={success_count}")
        await db.close()
    
    asyncio.run(_ingest())

def ingest_job_postings():
    """Task 2: Refresh job posting counts."""
    async def _ingest():
        from startupintel.ingestion.job_boards import JobBoardConnector
        db = AsyncSessionLocal()
        connector = JobBoardConnector()
        
        result = await db.execute(select(Startup).limit(500))
        startups = result.scalars().all()
        
        success_count = 0
        for startup in startups:
            if not startup.domain:
                continue
            try:
                jp = await connector.get_job_posting_count(startup.domain)
                if jp is not None:
                    success_count += 1
            except Exception as e:
                logger.warning(f"Job board ingest failed | startup={startup.id} | error={e}")
        
        logger.info(f"Job board ingest complete | total={len(startups)} | success={success_count}")
        await db.close()
    
    asyncio.run(_ingest())

def run_runway_bot_all():
    """Task 3: Run RunwayBot on all tracked startups."""
    async def _run():
        db = AsyncSessionLocal()
        neo4j = neo4j_driver()
        redis = redis_client()
        rag = RAGRetriever()
        llm = LLMClient()
        
        result = await db.execute(select(Startup).limit(500))
        startups = result.scalars().all()
        
        bot = RunwayBot(db, neo4j, redis, rag, llm)
        
        success_count = 0
        for startup in startups:
            try:
                bot_result = await bot.run(startup.id)
                if bot_result:
                    success_count += 1
            except Exception as e:
                logger.error(f"RunwayBot failed | startup={startup.id} | error={e}")
        
        logger.info(f"RunwayBot complete | total={len(startups)} | success={success_count}")
        await db.close()
        neo4j.close()
    
    asyncio.run(_run())

def alert_high_stress():
    """Task 4: Emit digest of high-stress startups to Slack."""
    # TODO: Implement Slack notification
    pass

task_1 = PythonOperator(
    task_id='ingest_linkedin_headcount',
    python_callable=ingest_linkedin_headcount,
    dag=dag
)

task_2 = PythonOperator(
    task_id='ingest_job_postings',
    python_callable=ingest_job_postings,
    dag=dag
)

task_3 = PythonOperator(
    task_id='run_runway_bot',
    python_callable=run_runway_bot_all,
    dag=dag
)

task_4 = PythonOperator(
    task_id='alert_high_stress',
    python_callable=alert_high_stress,
    dag=dag
)

task_1 >> task_2 >> task_3 >> task_4
```

**Success criteria:**

- [ ] DAG definition is valid Python (airflow dags list shows it)
- [ ] DAG scheduled for 6am UTC daily
- [ ] All 4 tasks connected in correct order
- [ ] Task 3 runs RunwayBot for 500+ startups within 1 hour

---

### Day 13 — Tests (6 test cases)

**File:** `tests/test_bots/test_runway_bot.py`

```python
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from startupintel.bots.runway_bot import RunwayBot
from startupintel.db.models import Startup, HeadcountSnapshot, StartupScore
from tests.conftest import *  # fixtures

@pytest.mark.asyncio
async def test_low_stress_startup(db, neo4j, redis, rag, llm):
    """Growing headcount + many jobs + positive sentiment = low stress."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="GrowthCo",
        domain="growthco.com",
        stage="series_a",
        employee_count=50
    )
    db.add(startup)
    await db.commit()
    
    # Mock signals for low stress
    signals = {
        "headcount_now": 60,
        "headcount_30d_ago": 50,
        "job_postings_now": 15,
        "job_postings_30d_ago": 10,
        "founder_sentiment_7d": 0.6,
        "domain_expiry_days": 300,
        "days_since_last_funding": 90
    }
    
    bot = RunwayBot(db, neo4j, redis, rag, llm)
    signal_breakdown = await bot.compute_score(signals)
    score = bot.normalize(signal_breakdown)
    
    assert score < 30, f"Expected low stress (< 30), got {score}"

@pytest.mark.asyncio
async def test_high_stress_startup(db, neo4j, redis, rag, llm):
    """Shrinking headcount + zero jobs + negative sentiment = high stress."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="FailingCo",
        domain="failingco.com",
        stage="series_b",
        employee_count=40
    )
    db.add(startup)
    await db.commit()
    
    signals = {
        "headcount_now": 25,
        "headcount_30d_ago": 40,
        "job_postings_now": 0,
        "job_postings_30d_ago": 8,
        "founder_sentiment_7d": -0.8,
        "domain_expiry_days": 15,
        "days_since_last_funding": 600
    }
    
    bot = RunwayBot(db, neo4j, redis, rag, llm)
    signal_breakdown = await bot.compute_score(signals)
    score = bot.normalize(signal_breakdown)
    
    assert score > 70, f"Expected high stress (> 70), got {score}"

@pytest.mark.asyncio
async def test_missing_headcount_signal_degraded(db, neo4j, redis, rag, llm):
    """Missing signal (None) → score computed without it, no crash."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="OffGrid",
        domain="offgrid.com",
        stage="seed"
    )
    db.add(startup)
    await db.commit()
    
    signals = {
        "headcount_now": None,  # LinkedIn scraper failed
        "headcount_30d_ago": None,
        "job_postings_now": 3,
        "job_postings_30d_ago": 2,
        "founder_sentiment_7d": 0.2,
        "domain_expiry_days": 200,
        "days_since_last_funding": 120
    }
    
    bot = RunwayBot(db, neo4j, redis, rag, llm)
    signal_breakdown = await bot.compute_score(signals)
    score = bot.normalize(signal_breakdown)
    
    # Score should exist, not be None or crash
    assert isinstance(score, float), f"Expected float score, got {type(score)}"
    assert 0 <= score <= 100, f"Score out of range: {score}"

@pytest.mark.asyncio
async def test_kafka_event_emitted_high_stress(db, neo4j, redis, rag, llm, kafka_producer_mock):
    """Score > 65 → Kafka event emitted."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="CrisisMode",
        domain="crisismode.com",
        stage="growth"
    )
    db.add(startup)
    await db.commit()
    
    signals = {
        "headcount_now": 20,
        "headcount_30d_ago": 45,  # -55%
        "job_postings_now": 0,
        "job_postings_30d_ago": 12,  # -100%
        "founder_sentiment_7d": -0.9,
        "domain_expiry_days": 10,  # < 30 days
        "days_since_last_funding": 700  # > 18 months
    }
    
    bot = RunwayBot(db, neo4j, redis, rag, llm)
    bot.events_producer = kafka_producer_mock  # Mock producer
    
    result = await bot.run(startup_id)
    
    # Verify event was emitted
    assert kafka_producer_mock.emit_startup_stress_high.called
    assert result.score > 65

@pytest.mark.asyncio
async def test_similar_cases_retrieved_from_rag(db, neo4j, redis, rag_mock, llm):
    """RAG retriever returns similar historical post-mortems."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="QuibiClone",
        domain="quibiclone.com",
        stage="series_b"
    )
    db.add(startup)
    await db.commit()
    
    signals = {
        "headcount_now": 30,
        "headcount_30d_ago": 80,
        "job_postings_now": 1,
        "job_postings_30d_ago": 20,
        "founder_sentiment_7d": -0.7,
        "domain_expiry_days": 45,
        "days_since_last_funding": 450
    }
    
    bot = RunwayBot(db, neo4j, redis, rag_mock, llm)
    rag_mock.search.return_value = [
        {
            "startup_name": "Quibi",
            "failure_cause": "no market need",
            "similarity": 0.87,
            "url": "https://medium.com/..."
        }
    ]
    
    result = await bot.run(startup_id)
    
    assert len(result.similar_cases) > 0
    assert result.similar_cases[0]["startup_name"] == "Quibi"
    assert result.similar_cases[0]["similarity"] > 0.75

@pytest.mark.asyncio
async def test_llm_diagnosis_generated(db, neo4j, redis, rag_mock, llm_mock):
    """LLM generates non-empty diagnosis string."""
    startup_id = uuid4()
    startup = Startup(
        id=startup_id,
        name="TestCo",
        domain="testco.com",
        stage="seed"
    )
    db.add(startup)
    await db.commit()
    
    signals = {
        "headcount_now": 8,
        "headcount_30d_ago": 10,
        "job_postings_now": 0,
        "job_postings_30d_ago": 2,
        "founder_sentiment_7d": 0.1,
        "domain_expiry_days": 180,
        "days_since_last_funding": 200
    }
    
    bot = RunwayBot(db, neo4j, redis, rag_mock, llm_mock)
    llm_mock.generate_diagnosis.return_value = (
        "Startup shows stress signals: headcount declined 20%, job postings dropped 100%. "
        "Founder sentiment remains neutral. Domain renewal not immediate concern. "
        "Recommendation: monitor next 30 days, investigate if more indicators emerge."
    )
    
    result = await bot.run(startup_id)
    
    assert isinstance(result.llm_diagnosis, str)
    assert len(result.llm_diagnosis) > 50
    assert "Recommendation" in result.llm_diagnosis or "recommendation" in result.llm_diagnosis.lower()
```

**Success criteria:**

- [ ] All 6 tests pass with pytest
- [ ] Coverage: `test_low_stress`, `test_high_stress`, `test_missing_signal`, `test_kafka`, `test_rag`, `test_llm`
- [ ] Mock fixtures work (kafka_producer_mock, rag_mock, llm_mock)
- [ ] Tests run in < 5 seconds total

---

### Day 14 — Integration Test + Cleanup

**Objective:** End-to-end test. RunwayBot runs, scores persisted, events emitted, downstream bots triggered.

**Success criteria (full integration):**

- [ ] `docker-compose up` — all services healthy
- [ ] `python scripts/seed_database.py` — 100 test startups created
- [ ] `GET /startup/{id}/stress` returns 200 with RunwayBotOutput
- [ ] Response cached in Redis (verify with `redis-cli`)
- [ ] Score written to Postgres `startup_scores` table
- [ ] Score written to Neo4j Startup node (runway_score property)
- [ ] Kafka event emitted to `startup.stress.high` topic (verify with kafka-console-consumer)
- [ ] Downstream bots (PivotBot, ObituaryBot, AcquiBot) triggered by handler
- [ ] All 6 test_runway_bot.py tests pass
- [ ] Airflow DAG validates (airflow dags list shows run_runway_bot)

---

## Bot 2 — ObituaryBot (Days 15–21)

**Reference:** CLAUDE.md § Bot 2 — ObituaryBot (lines 477–540)

### Summary

ObituaryBot is the first bot to demonstrate RAG + LLM integration. It depends on:
- Post-mortem corpus (3,000+ startup failures scraped)
- FAISS vector index (embeddings of post-mortems)
- LLM extractor (structured extraction from raw post-mortem text)
- BERTopic (failure taxonomy clustering)

**Day 15–16:** Scrape & prepare post-mortem corpus.
**Day 17:** LLM extraction prompt + BERTopic clustering.
**Day 18:** ObituaryBot scoring + FAISS index building.
**Day 19:** API endpoint + Kafka event.
**Day 20:** Airflow DAG (weekly, on-demand refresh).
**Day 21:** 6 test cases.

---

## Bot 3 — TermBot (Days 22–26)

**Reference:** CLAUDE.md § Bot 3 — TermBot (lines 544–612)

### Summary

TermBot is **on-demand only** (no scheduled DAG). It decodes PDF term sheets clause-by-clause.

**Day 22:** 12-clause LLM extraction prompts (one per clause).
**Day 23:** Scoring logic + market benchmark corpus (SEC EDGAR).
**Day 24:** PDF upload endpoint (`POST /termsheet`).
**Day 25:** Red flag detection + Kafka `termsheet.red_flag` event.
**Day 26:** 6 test cases (founder-friendly, predatory, all 12 clauses extracted).

---

## Bot 4 — PivotBot (Days 27–33)

**Reference:** CLAUDE.md § Bot 4 — PivotBot (lines 616–679)

### Summary

PivotBot reconstructs pivot history from 6 sources: Wayback Machine, ProductHunt, App Store, GitHub, Twitter, Crunchbase.

**Day 27:** Wayback Machine connector + cosine similarity for homepage snapshots.
**Day 28:** ProductHunt launches + App Store version history.
**Day 29:** GitHub repo events + Twitter keyword shifts (quarterly windows).
**Day 30:** Deduplication logic (events within 30 days = same pivot).
**Day 31:** Pivot type classification (5 types: customer_segment, product, revenue_model, technology, geography).
**Day 32:** API endpoints + Kafka `startup.pivot.detected` event.
**Day 33:** 6 test cases.

---

## Bot 5 — PMFBot (Days 34–40)

**Reference:** CLAUDE.md § Bot 5 — PMFBot (lines 683–737)

### Summary

PMFBot aggregates 8 signals + detects changepoints using PELT algorithm (ruptures library).

**Day 34:** 8 signal connectors (App Store, G2, Google Trends, GitHub, Stack Overflow, Reddit, ProductHunt, Twitter).
**Day 35:** Signal normalization (each 0-1 by percentile vs. industry baseline).
**Day 36:** Changepoint detection (PELT algorithm on rolling 90-day window).
**Day 37:** PMF status classification (pre_pmf → approaching → strong → clear).
**Day 38:** Kafka `startup.pmf.inflection` event (changepoint OR score crosses 60).
**Day 39:** API endpoints (`GET /startup/{id}/pmf` + historical scores).
**Day 40:** 6 test cases.

---

## Bot 6 — AcceleratorBot (Days 41–46)

**Reference:** CLAUDE.md § Bot 6 — AcceleratorBot (lines 741–784)

### Summary

AcceleratorBot ranks 400+ accelerators by outcome ROI. Monthly refresh, no real-time triggers.

**Day 41:** Seed data (`data/accelerators_seed.csv` — 400+ accelerators + cohort lists).
**Day 42–43:** Compute 7 metrics per accelerator (follow-on rate, time-to-Series-A, survival, unicorn rate, etc.).
**Day 44:** Normalization (industry, geography, vintage year, stage adjustments).
**Day 45:** Leaderboard ranking + confidence intervals (Wilson score).
**Day 46:** API endpoints (`GET /accelerator/rankings`, `/recommend`). Monthly DAG.

---

## Bot 7 — InvestorBot (Days 47–53)

**Reference:** CLAUDE.md § Bot 7 — InvestorBot (lines 788–840)

### Summary

InvestorBot scores investors by network centrality (betweenness, eigenvector, diversity, value-add).

**Day 47:** Bipartite graph construction (investors ↔ startups from Crunchbase).
**Day 48:** Graph projection (investor-investor graph).
**Day 49:** NetworkX centrality computation (betweenness, eigenvector).
**Day 50:** Portfolio diversity (Gini coefficient) + value-add proxy (LinkedIn intros + Twitter engagement).
**Day 51:** D3 force graph visualization payload.
**Day 52:** API endpoints (`GET /investor/rankings`, `/recommend`, `/network`).
**Day 53:** 6 test cases.

---

## Bot 8 — AcquiBot (Days 54–60)

**Reference:** CLAUDE.md § Bot 8 — AcquiBot (lines 844–916)

### Summary

AcquiBot predicts acqui-hire probability using XGBoost trained on 500+ confirmed acqui-hires.

**Day 54:** Feature engineering (team prestige, tech rarity, network overlap, financial stress).
**Day 55:** XGBoost model training (historical 2015–2021, test 2022–2024).
**Day 56:** SHAP value computation (interpretability per prediction).
**Day 57:** Acquirer matching (top-50 acquirers, tech fit + team fit + network overlap).
**Day 58:** Kafka `startup.acqui.signal` event (probability > 0.60).
**Day 59:** API endpoints (`GET /startup/{id}/acqui` + acquirer shortlist).
**Day 60:** 6 test cases + monthly retraining DAG.

---

## Cross-Bot Integration (Days 61–65)

**Objective:** Wire all Kafka events. Synthesizer generates unified briefs.

**Day 61–62:** Complete EventHandler for all 7 topics.
**Day 63:** LLM Synthesizer implementation.
**Day 64:** `GET /startup/{id}/brief` endpoint (waits for all bot scores, then synthesizes).
**Day 65:** Integration test: stress event → 3 bots triggered → synthesizer generates brief.

---

## Product & Deployment (Days 66–70)

**Day 66–67:** Slack digest bot (`startupintel/slack/bot.py`).
**Day 68:** Prometheus metrics + Grafana dashboard.
**Day 69:** Terraform deploy config (AWS ECS + RDS + ElastiCache).
**Day 70:** HuggingFace dataset upload (ObituaryBot corpus). arXiv abstract drafted.

---

## Per-Bot Build Order Summary

| Phase | Days | Bot | Deliverable |
|---|---|---|---|
| 1 | 1–7 | — | Infrastructure (docker-compose, all schemas, RAG, LLM) |
| 2 | 8–14 | RunwayBot | 5 connectors, scoring, API, DAG, 6 tests |
| 3 | 15–21 | ObituaryBot | Corpus, FAISS, LLM extraction, 6 tests |
| 4 | 22–26 | TermBot | 12-clause analysis, PDF upload, 6 tests |
| 5 | 27–33 | PivotBot | 6-source detection, dedup, 5 pivot types, 6 tests |
| 6 | 34–40 | PMFBot | 8-signal aggregator, PELT changepoint, 6 tests |
| 7 | 41–46 | AcceleratorBot | 400+ accelerators, ROI ranking, leaderboard |
| 8 | 47–53 | InvestorBot | NetworkX centrality, D3 viz, ranking |
| 9 | 54–60 | AcquiBot | XGBoost model, SHAP, acquirer matching, 6 tests |
| 10 | 61–70 | All | Synthesis, Slack, Prometheus, deploy |

---

## Key Integration Points Between Bots

```
RunwayBot (Day 8–14)
  └─ emits: startup.stress.high
     └─ triggers: PivotBot, ObituaryBot, AcquiBot

PivotBot (Day 27–33)
  └─ emits: startup.pivot.detected
     └─ triggers: ObituaryBot, PMFBot

ObituaryBot (Day 15–21)
  └─ emits: startup.obituary.high_match
     └─ triggers: none (terminal)

PMFBot (Day 34–40)
  └─ emits: startup.pmf.inflection
     └─ triggers: InvestorBot

AcquiBot (Day 54–60)
  └─ emits: startup.acqui.signal
     └─ triggers: InvestorBot

TermBot (Day 22–26)
  └─ emits: termsheet.red_flag
     └─ triggers: none (alert only)

AcceleratorBot (Day 41–46)
  └─ no events (monthly, slow-moving)

InvestorBot (Day 47–53)
  └─ emits: investor.network.updated
     └─ triggers: none

Synthesizer (Day 61–65)
  └─ reads: all bot scores for a startup
  └─ generates: unified brief
  └─ API: GET /startup/{id}/brief
```

---

## Testing Strategy

**Per-bot minimum: 6 test cases**
```
test_{bot}_low_score()          → baseline, no signals
test_{bot}_high_score()         → max signals
test_{bot}_missing_signal()     → graceful degradation
test_{bot}_kafka_event()        → event emitted if threshold crossed
test_{bot}_rag_retrieval()      → RAG returns similar cases
test_{bot}_llm_diagnosis()      → diagnosis generated and non-empty
```

**Total tests:** 8 bots × 6 tests = 48 minimum. Run nightly.

---

## Success Criteria — Full Build

**Day 14 (RunwayBot):**
- [ ] `pytest tests/test_bots/test_runway_bot.py -v` — all 6 pass
- [ ] `GET /startup/{id}/stress` returns 200
- [ ] Score cached in Redis (< 50ms on hit)
- [ ] Score in Postgres + Neo4j
- [ ] Kafka event fires for score > 65

**Day 21 (ObituaryBot):**
- [ ] 1,000+ post-mortems in FAISS index
- [ ] `pytest tests/test_bots/test_obituary_bot.py -v` — all 6 pass
- [ ] `GET /startup/{id}/obituary` returns similar cases + score

**Day 26 (TermBot):**
- [ ] `POST /termsheet` accepts PDF
- [ ] 12 clauses analyzed
- [ ] Red flags detected for predatory clauses
- [ ] `pytest tests/test_bots/test_term_bot.py -v` — all 6 pass

**Day 33 (PivotBot):**
- [ ] Wayback snapshots fetched and compared
- [ ] Pivots detected across all 6 sources
- [ ] Deduplication logic working
- [ ] `pytest tests/test_bots/test_pivot_bot.py -v` — all 6 pass

**Day 40 (PMFBot):**
- [ ] 8 signals aggregated
- [ ] Changepoint detected on synthetic time-series
- [ ] `pytest tests/test_bots/test_pmf_bot.py -v` — all 6 pass

**Day 46 (AcceleratorBot):**
- [ ] 400+ accelerators ranked
- [ ] Normalization applied (industry, geo, vintage)
- [ ] Leaderboard endpoints working

**Day 53 (InvestorBot):**
- [ ] Graph projection valid
- [ ] Centrality scores computed
- [ ] D3 viz payload generated

**Day 60 (AcquiBot):**
- [ ] XGBoost model trained + loaded
- [ ] SHAP values computed per prediction
- [ ] Acquirer shortlist ranked
- [ ] `pytest tests/test_bots/test_acqui_bot.py -v` — all 6 pass

**Day 70 (Full deployment):**
- [ ] All 8 bots integrated via Kafka
- [ ] Synthesizer generates unified brief
- [ ] Slack bot sends weekly digests
- [ ] Prometheus metrics exposed
- [ ] Terraform deploy to AWS works
- [ ] HuggingFace dataset public
- [ ] arXiv abstract submitted

---

## Development Checklist

Use this checklist day-by-day to track progress:

```
Phase 1 (Days 1–7): Infrastructure
  ☐ docker-compose.yml (Postgres, Neo4j, Redis, Kafka, Zookeeper)
  ☐ startupintel/db/models.py
  ☐ alembic migrations
  ☐ startupintel/rag/indexer.py + retriever.py (FAISS index)
  ☐ startupintel/llm/client.py (Groq + Ollama)
  ☐ startupintel/events/producer.py + consumer.py
  ☐ scripts/seed_database.py (100 test startups)

Phase 2 (Days 8–14): RunwayBot
  ☐ 5 connectors (linkedin, job_boards, twitter, domain_whois, crunchbase)
  ☐ RunwayBot.compute_score() + weights
  ☐ GET /startup/{id}/stress endpoint
  ☐ Kafka startup.stress.high event
  ☐ Airflow DAG (daily 6am UTC)
  ☐ 6 test cases + conftest fixtures
  ☐ Integration test (end-to-end)

Phase 3 (Days 15–21): ObituaryBot
  ☐ scrape_postmortems.py (500+ Medium, HN, blogs)
  ☐ LLM extraction prompt (12-category taxonomy)
  ☐ BERTopic clustering
  ☐ FAISS index rebuild
  ☐ ObituaryBot.compute_score() + matching
  ☐ API endpoints (GET /obituary/*)
  ☐ Kafka startup.obituary.high_match event
  ☐ 6 test cases

Phase 4 (Days 22–26): TermBot
  ☐ 12-clause extraction prompts
  ☐ SEC EDGAR corpus (market benchmarks)
  ☐ PDF upload endpoint (POST /termsheet)
  ☐ Clause-by-clause scoring
  ☐ Red flag detection + Kafka event
  ☐ 6 test cases

Phase 5 (Days 27–33): PivotBot
  ☐ 6 signal connectors (wayback, pH, app_store, github, twitter, crunchbase)
  ☐ Cosine similarity (homepage snapshots)
  ☐ Pivot type classification (5 types)
  ☐ Deduplication logic (30-day window)
  ☐ Kafka startup.pivot.detected event
  ☐ API endpoints (GET /startup/{id}/pivot*)
  ☐ 6 test cases

Phase 6 (Days 34–40): PMFBot
  ☐ 8 signal connectors
  ☐ Signal normalization (percentile vs baseline)
  ☐ PELT changepoint detection (ruptures)
  ☐ PMF status thresholds
  ☐ Kafka startup.pmf.inflection event
  ☐ API endpoints (GET /startup/{id}/pmf*)
  ☐ 6 test cases

Phase 7 (Days 41–46): AcceleratorBot
  ☐ data/accelerators_seed.csv (400+ accelerators)
  ☐ 7 metrics computation (outcomes)
  ☐ Normalization (industry, geo, vintage, stage)
  ☐ ROI score + confidence intervals
  ☐ API endpoints (leaderboard, recommend)
  ☐ Monthly Airflow DAG

Phase 8 (Days 47–53): InvestorBot
  ☐ Crunchbase co-investment graph
  ☐ Bipartite → unipartite projection
  ☐ NetworkX centrality metrics
  ☐ Portfolio diversity (Gini)
  ☐ Value-add proxy (LinkedIn + Twitter)
  ☐ D3 force graph payload
  ☐ API endpoints (ranking, recommend, network)
  ☐ 6 test cases

Phase 9 (Days 54–60): AcquiBot
  ☐ Feature engineering (4 groups)
  ☐ XGBoost training script (Crunchbase 2015–2021)
  ☐ SHAP value computation
  ☐ Acquirer matching (top-50)
  ☐ Kafka startup.acqui.signal event
  ☐ API endpoints
  ☐ Monthly retraining DAG
  ☐ 6 test cases

Phase 10 (Days 61–70): Synthesis + Deploy
  ☐ EventHandler (all 7 Kafka topics)
  ☐ LLM Synthesizer implementation
  ☐ GET /startup/{id}/brief endpoint
  ☐ Slack digest bot
  ☐ Prometheus metrics + Grafana dashboard
  ☐ Terraform deploy config (ECS + RDS + ElastiCache)
  ☐ HuggingFace dataset release
  ☐ arXiv abstract
  ☐ Final integration test
```

---

## How to Use This Document

1. **Read CLAUDE.md fully** (all 1,030 lines) to understand the platform architecture.

2. **Read this document** (BOT BUILD PLANS) for granular day-by-day coding roadmap.

3. **Start with Day 1–7 (Infrastructure):**
   - Use the checklist above.
   - All downstream bots depend on these 7 days.
   - Don't skip any step.

4. **For each bot (Days 8–60):**
   - Follow the day-by-day breakdown provided.
   - Refer back to CLAUDE.md for detailed specs (signals, weights, formulas, prompts).
   - Write the exact functions/classes listed.
   - Run tests as you go (pytest after each day).
   - Don't move to the next bot until all 6 tests pass.

5. **Days 61–70 (Synthesis + Deploy):**
   - Wire Kafka events (all 7 topics).
   - Implement LLM Synthesizer.
   - Deploy to AWS via Terraform.
   - Release dataset to HuggingFace.

---

## Claude Code Execution (Recommended Workflow)

### Session 1 (Days 1–7)
```
claude: "Read CLAUDE.md and BOT BUILD PLANS. Build infrastructure (docker-compose, models, migrations, RAG, LLM). Success: docker-compose up, all services healthy, 100 startups seeded."
```

### Session 2 (Days 8–14)
```
claude: "Implement RunwayBot fully. Reference CLAUDE.md § Bot 1 and BOT BUILD PLANS § Bot 1 (Days 8–14). Build 5 connectors, scoring, API, DAG. All 6 tests pass. Success: GET /startup/{id}/stress returns 200."
```

### Session 3 (Days 15–21)
```
claude: "Implement ObituaryBot. Reference CLAUDE.md § Bot 2 and BOT BUILD PLANS § Bot 2 (Days 15–21). Scrape 1,000+ post-mortems, build FAISS index, implement scoring. All 6 tests pass."
```

Continue this pattern for each bot.

### Final Session (Days 61–70)
```
claude: "Wire all Kafka events. Implement LLM Synthesizer. Deploy to AWS. Test end-to-end: stress event → 3 bots triggered → synthesizer generates brief. Release dataset. Done."
```

---

**This is the complete execution plan for StartupIntel. Print this document. Pin it to your desk. Follow it line by line.**

**Estimated total development time: 10 weeks, one developer or pair programming.**

---

## Appendix: Code Snippet Templates

### Template: BaseConnector

```python
from abc import ABC, abstractmethod
from redis import Redis

class BaseConnector(ABC):
    def __init__(self, redis: Redis = None):
        self.redis = redis
    
    @abstractmethod
    async def fetch(self, *args, **kwargs):
        """Fetch data from external source."""
        pass
    
    async def get_cached(self, key: str, ttl_seconds: int = 3600):
        """Get from cache, or None if miss."""
        if self.redis:
            return await self.redis.get(key)
        return None
    
    async def set_cached(self, key: str, value: str, ttl_seconds: int = 3600):
        """Set value in cache with TTL."""
        if self.redis:
            await self.redis.setex(key, ttl_seconds, value)
```

### Template: Pydantic Schema

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class BotOutputBase(BaseModel):
    startup_id: UUID
    score: float
    computed_at: datetime
    
    class Config:
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}
```

### Template: Pytest Fixture

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def db():
    """In-memory SQLite test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

---

**End of BOT BUILD PLANS**
