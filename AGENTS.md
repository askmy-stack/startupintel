# AGENTS.md — StartupIntel

## What This Is

StartupIntel is an open-source startup intelligence platform. Eight specialized ML bots ingest public signals about startups and unify them into a single intelligence layer with cross-bot reasoning.

**Read this file fully before writing any code.**

---

## Repo Structure

```
startupintel/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── alembic.ini
│
├── startupintel/
│   ├── config.py                         # Pydantic Settings — all config from .env
│   ├── db/
│   │   ├── postgres.py                   # SQLAlchemy async engine
│   │   ├── neo4j.py                      # Neo4j async driver
│   │   ├── redis.py                      # Redis client
│   │   └── models.py                     # All ORM models — BUILD THIS FIRST
│   ├── ingestion/
│   │   ├── base.py                       # Abstract BaseConnector
│   │   ├── crunchbase.py                 # Funding, exits, founding data
│   │   ├── linkedin.py                   # Headcount time-series (Playwright)
│   │   ├── github.py                     # Stars, commits, contributors
│   │   ├── sec_edgar.py                  # Term sheets, S-1 filings
│   │   ├── wayback.py                    # Historical website snapshots
│   │   ├── app_store.py                  # Review velocity, version history
│   │   ├── producthunt.py                # Launch history, upvotes
│   │   ├── twitter.py                    # Founder sentiment
│   │   ├── job_boards.py                 # Job posting counts
│   │   ├── domain_whois.py               # Domain renewal status
│   │   └── g2_capterra.py                # Review ratings
│   ├── graph/
│   │   ├── schema.py
│   │   ├── queries.py
│   │   └── builder.py
│   ├── rag/
│   │   ├── indexer.py
│   │   ├── retriever.py
│   │   └── corpus/
│   │       ├── postmortems/
│   │       ├── termsheets/
│   │       └── pivots/
│   ├── llm/
│   │   ├── client.py                     # Groq + Ollama unified
│   │   ├── extractor.py
│   │   ├── narrator.py
│   │   └── synthesizer.py                # Cross-bot unified brief
│   ├── bots/
│   │   ├── base.py                       # Abstract BaseBot
│   │   ├── runway_bot.py
│   │   ├── obituary_bot.py
│   │   ├── term_bot.py
│   │   ├── pivot_bot.py
│   │   ├── pmf_bot.py
│   │   ├── accelerator_bot.py
│   │   ├── investor_bot.py
│   │   └── acqui_bot.py
│   ├── events/
│   │   ├── producer.py
│   │   ├── consumer.py
│   │   ├── topics.py
│   │   └── handlers.py
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── startup.py
│   │       ├── investor.py
│   │       ├── accelerator.py
│   │       ├── termsheet.py
│   │       └── health.py
│   ├── airflow/
│   │   └── dags/
│   │       ├── run_runway_bot.py
│   │       ├── run_obituary_bot.py
│   │       ├── run_term_bot.py
│   │       ├── run_pivot_bot.py
│   │       ├── run_pmf_bot.py
│   │       ├── run_accelerator_bot.py
│   │       ├── run_investor_bot.py
│   │       ├── run_acqui_bot.py
│   │       └── weekly_digest.py
│   ├── slack/
│   │   ├── bot.py
│   │   ├── digest.py
│   │   └── commands.py
│   └── scoring/
│       ├── normalizer.py
│       ├── weights.py
│       └── backtest.py
│
├── tests/
│   ├── conftest.py
│   ├── test_bots/
│   │   ├── test_runway_bot.py
│   │   ├── test_obituary_bot.py
│   │   ├── test_term_bot.py
│   │   ├── test_pivot_bot.py
│   │   ├── test_pmf_bot.py
│   │   ├── test_accelerator_bot.py
│   │   ├── test_investor_bot.py
│   │   └── test_acqui_bot.py
│   ├── test_api/
│   │   └── test_routes.py
│   └── fixtures/
│       ├── sample_startups.json
│       ├── sample_termsheet.pdf
│       └── sample_signals.json
│
├── scripts/
│   ├── seed_database.py
│   ├── scrape_postmortems.py
│   ├── train_acqui_model.py
│   └── benchmark_bots.py
│
└── notebooks/
    ├── 01_runway_signal_analysis.ipynb
    ├── 02_pmf_signal_correlation.ipynb
    ├── 03_obituary_clustering.ipynb
    ├── 04_investor_network_analysis.ipynb
    └── 05_acqui_scoring_validation.ipynb
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Primary DB | PostgreSQL 16 |
| Graph DB | Neo4j 5.x |
| Cache + Queue | Redis 7 |
| Event streaming | Apache Kafka 3.6 |
| Orchestration | Apache Airflow 2.8 |
| Embeddings | sentence-transformers (all-mpnet-base-v2) |
| Vector index | FAISS (faiss-cpu) |
| LLM fast | Groq — llama-3.3-70b-versatile |
| LLM local | Ollama — gemma3:4b |
| API | FastAPI + uvicorn |
| Graph ML | NetworkX + PyTorch Geometric |
| Scraping | Playwright |
| Monitoring | Prometheus + Grafana |

---

## Environment Variables

```bash
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/startupintel
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=startupintel-bots
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
EMBEDDING_MODEL=all-mpnet-base-v2
FAISS_INDEX_PATH=./data/faiss_index
CRUNCHBASE_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
TWITTER_BEARER_TOKEN=your_token_here
PRODUCTHUNT_TOKEN=your_token_here
SEC_EDGAR_USER_AGENT=StartupIntel contact@youremail.com
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
SLACK_DIGEST_CHANNEL=#startupintel
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=generate_with_openssl_rand_hex_32
RUNWAY_WEIGHT_HEADCOUNT=0.35
RUNWAY_WEIGHT_JOB_POSTINGS=0.25
RUNWAY_WEIGHT_SENTIMENT=0.20
RUNWAY_WEIGHT_DOMAIN=0.10
RUNWAY_WEIGHT_FUNDING_RECENCY=0.10
PMF_WEIGHT_REVIEWS=0.25
PMF_WEIGHT_G2=0.20
PMF_WEIGHT_SEARCH=0.20
PMF_WEIGHT_GITHUB=0.15
PMF_WEIGHT_STACKOVERFLOW=0.10
PMF_WEIGHT_REDDIT=0.05
PMF_WEIGHT_PRODUCTHUNT=0.03
PMF_WEIGHT_TWITTER=0.02
ACQUI_WEIGHT_TEAM=0.30
ACQUI_WEIGHT_TECH=0.25
ACQUI_WEIGHT_NETWORK=0.25
ACQUI_WEIGHT_FINANCIAL=0.20
INVESTOR_WEIGHT_BETWEENNESS=0.35
INVESTOR_WEIGHT_EIGENVECTOR=0.25
INVESTOR_WEIGHT_DIVERSITY=0.20
INVESTOR_WEIGHT_VALUE_ADD=0.20
RUNWAY_HIGH_STRESS_THRESHOLD=65
PMF_INFLECTION_THRESHOLD=15
ACQUI_HIGH_PROBABILITY_THRESHOLD=60
```

---

## Core Data Models (startupintel/db/models.py)

```python
class Startup(Base):
    __tablename__ = "startups"
    id: UUID
    name: str
    domain: str (unique)
    crunchbase_id: Optional[str]
    founded_year: Optional[int]
    industry: Optional[str]
    stage: Optional[str]               # seed|series_a|series_b|growth
    hq_city: Optional[str]
    hq_country: Optional[str]
    employee_count: Optional[int]
    total_funding_usd: Optional[float]
    last_funding_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class StartupScore(Base):
    __tablename__ = "startup_scores"
    id: UUID
    startup_id: UUID (FK → startups)
    bot_name: str                      # runway|obituary|term|pivot|pmf|accelerator|investor|acqui
    score: float                       # 0-100
    signal_breakdown: JSONB
    llm_diagnosis: Optional[str]
    similar_cases: JSONB
    raw_signals: JSONB
    computed_at: datetime

class Investor(Base):
    __tablename__ = "investors"
    id: UUID
    name: str
    firm: Optional[str]
    linkedin_url: Optional[str]
    crunchbase_id: Optional[str]
    centrality_score: Optional[float]
    value_add_score: Optional[float]
    betweenness: Optional[float]
    eigenvector: Optional[float]
    portfolio_count: Optional[int]
    updated_at: datetime

class Accelerator(Base):
    __tablename__ = "accelerators"
    id: UUID
    name: str
    location: str
    cohort_count: int
    follow_on_rate: Optional[float]
    median_time_to_series_a_months: Optional[float]
    survival_rate_3yr: Optional[float]
    unicorn_rate: Optional[float]
    shutdown_rate: Optional[float]
    roi_score: Optional[float]
    industry_focus: Optional[str]
    stage_focus: Optional[str]
    updated_at: datetime

class TermSheetAnalysis(Base):
    __tablename__ = "termsheet_analyses"
    id: UUID
    startup_id: Optional[UUID]
    raw_text: str
    founder_friendliness_score: float
    red_flags: JSONB
    clause_scores: JSONB
    market_benchmark: JSONB
    llm_diagnosis: Optional[str]
    analyzed_at: datetime

class HeadcountSnapshot(Base):
    __tablename__ = "headcount_snapshots"
    id: UUID
    startup_id: UUID (FK)
    headcount: int
    snapshot_date: datetime
    source: str

class SignalEvent(Base):
    __tablename__ = "signal_events"
    id: UUID
    startup_id: UUID (FK)
    event_type: str
    payload: JSONB
    emitted_at: datetime
```

---

## Neo4j Graph Schema

```cypher
CREATE CONSTRAINT startup_id IF NOT EXISTS FOR (s:Startup) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT investor_id IF NOT EXISTS FOR (i:Investor) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT founder_id IF NOT EXISTS FOR (f:Founder) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT accelerator_id IF NOT EXISTS FOR (a:Accelerator) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT acquirer_id IF NOT EXISTS FOR (q:Acquirer) REQUIRE q.id IS UNIQUE;

(:Startup {id, name, domain, stage, industry,
  runway_score, pmf_score, acqui_probability,
  failure_pattern_match, pivot_count})
(:Founder {id, name, linkedin_url})
(:Investor {id, name, firm, centrality_score, value_add_score})
(:Accelerator {id, name, location, roi_score})
(:Acquirer {id, name, domain})

(:Founder)-[:FOUNDED {date}]->(:Startup)
(:Startup)-[:RAISED_FROM {round, amount_usd, date}]->(:Investor)
(:Startup)-[:WENT_THROUGH {year, cohort}]->(:Accelerator)
(:Startup)-[:ACQUIRED_BY {date, amount_usd}]->(:Acquirer)
(:Startup)-[:PIVOTED_TO {date, pivot_type}]->(:Startup)
(:Investor)-[:CO_INVESTED_WITH {deal_count}]->(:Investor)
(:Founder)-[:WORKED_AT {role, start, end}]->(:Startup)
(:Investor)-[:PORTFOLIO_AT {role}]->(:Acquirer)
```

---

## BaseBot Abstract Class (startupintel/bots/base.py)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass
class BotResult:
    startup_id: UUID
    bot_name: str
    score: float
    signal_breakdown: dict[str, float]
    raw_signals: dict
    similar_cases: list[dict]
    llm_diagnosis: str
    computed_at: datetime

class BaseBot(ABC):
    name: str
    version: str = "0.1.0"
    required_signals: list[str]

    def __init__(self, db, neo4j, redis, rag_retriever, llm_client):
        self.db = db
        self.neo4j = neo4j
        self.redis = redis
        self.rag = rag_retriever
        self.llm = llm_client

    async def run(self, startup_id: UUID) -> BotResult:
        cached = await self.redis.get(f"{self.name}:{startup_id}")
        if cached:
            return BotResult(**cached)
        raw_signals = await self.fetch_signals(startup_id)
        signal_breakdown = await self.compute_score(raw_signals)
        score = self.normalize(signal_breakdown)
        similar_cases = await self.rag.search(self.build_rag_query(raw_signals), top_k=5)
        diagnosis = await self.llm.generate_diagnosis(
            self.name, score, signal_breakdown, similar_cases,
            self.diagnosis_prompt_template()
        )
        result = BotResult(startup_id, self.name, score, signal_breakdown,
                          raw_signals, similar_cases, diagnosis, datetime.utcnow())
        await self.persist(result)
        await self.write_to_graph(result)
        await self.redis.setex(f"{self.name}:{startup_id}", 3600, result)
        await self.maybe_emit_event(result)
        return result

    def normalize(self, signal_breakdown: dict[str, float]) -> float:
        weights = self.get_weights()
        raw = sum(signal_breakdown[k] * weights[k] for k in weights)
        return min(100.0, max(0.0, raw * 100))

    @abstractmethod
    async def fetch_signals(self, startup_id: UUID) -> dict: ...
    @abstractmethod
    async def compute_score(self, raw: dict) -> dict[str, float]: ...
    @abstractmethod
    def get_weights(self) -> dict[str, float]: ...
    @abstractmethod
    def build_rag_query(self, raw: dict) -> str: ...
    @abstractmethod
    def diagnosis_prompt_template(self) -> str: ...
    @abstractmethod
    async def maybe_emit_event(self, result: BotResult) -> None: ...
```

---

## Bot 1 — RunwayBot

**File:** `startupintel/bots/runway_bot.py`
**Purpose:** Detect financial stress 60–90 days before public announcement.
**Connectors:** linkedin.py, job_boards.py, twitter.py, domain_whois.py, crunchbase.py

**Signals + weights:**
```python
WEIGHTS = {
    "headcount": 0.35,        # LinkedIn headcount % change (negative = stress)
    "job_postings": 0.25,     # Job board posting count change
    "sentiment": 0.20,        # Founder Twitter VADER sentiment
    "domain_renewal": 0.10,   # Days until domain expires (<30 = stress)
    "funding_recency": 0.10   # Days since last raise (>18mo = stress)
}
```

**Scoring formula:**
```python
# headcount_score = max(0, min(1, (-hc_delta_pct + 0.3) / 0.6))
# job_score = max(0, min(1, (-jp_delta_pct + 0.5) / 1.0))
# sentiment_score = max(0, min(1, (-founder_sentiment + 1) / 2))
# domain_score = max(0, min(1, (90 - days_until_expiry) / 90))
# funding_score = max(0, min(1, (days_since_raise - 365) / 365))
```

**LLM diagnosis prompt:**
```
You are a startup analyst detecting financial distress signals.
Startup runway stress score: {score}/100
Headcount change (30d): {headcount_delta}%
Job postings change (30d): {job_posting_delta}%
Founder sentiment (7d avg): {sentiment}
Domain expires in: {domain_expiry_days} days
Days since last funding: {days_since_funding}
Most similar historical cases: {similar_cases}

Write 3 sentences:
1. What signals indicate about current financial state
2. Strongest indicator and why
3. Recommended action (monitor/investigate/alert)
Be specific. Reference numbers. No filler.
```

**Output:**
```python
class RunwayBotOutput(BaseModel):
    startup_id: UUID
    score: float                    # 0-100
    risk_level: str                 # low|monitor|elevated|high
    signal_breakdown: dict[str, float]
    headcount_delta_pct: float
    job_posting_delta_pct: float
    founder_sentiment: float
    domain_expiry_days: int
    days_since_funding: int
    similar_cases: list[SimilarCase]
    llm_diagnosis: str
    computed_at: datetime
```

**Kafka:** `startup.stress.high` (score > 65) → triggers PivotBot, ObituaryBot, AcquiBot
**API:** `GET /startup/{id}/stress`
**DAG:** Daily 6am UTC — ingest_linkedin → ingest_job_boards → run_runway_bot
**Tests:** test_low_stress, test_high_stress, test_missing_signal, test_kafka_fired, test_rag_retrieved, test_diagnosis_generated

---

## Bot 2 — ObituaryBot

**File:** `startupintel/bots/obituary_bot.py`
**Purpose:** Mine 3,000+ startup post-mortems. Match any startup against historical failures.
**Connectors:** scripts/scrape_postmortems.py (one-time + monthly), crunchbase.py

**Post-mortem extraction prompt:**
```
Extract failure data from this startup post-mortem. Return JSON only.
Post-mortem: {text}
Return: {
  "startup_name": str,
  "failure_causes": ["primary", "secondary"],  # from taxonomy
  "stage_at_death": "pre_seed|seed|series_a|series_b|growth",
  "industry": str,
  "team_size_at_death": int | null,
  "runway_months_at_death": int | null,
  "key_lesson": "1 sentence",
  "had_revenue": true | false | null
}
Taxonomy: no_market_need|ran_out_of_cash|wrong_team|competition|
pricing_model|poor_product|bad_timing|pivot_failure|
legal_regulatory|burnout|failed_to_raise|founder_conflict
```

**Scoring:**
```python
# query = "{industry} {stage} {failure_signals_text}"
# top_match_similarity = cosine_sim(query_embedding, faiss_search top-1)
# avg_top3_similarity = mean cosine_sim of top 3 matches
# cause_concentration = 1 - (unique_causes_in_top5 / 5)
WEIGHTS = {"top_match_similarity": 0.50, "avg_top3_similarity": 0.30, "cause_concentration": 0.20}
```

**LLM diagnosis prompt:**
```
Startup: {name} | Industry: {industry} | Stage: {stage}
Current signals: {failure_signals_summary}
Top 3 similar historical failures: {similar_cases}

Write 3 sentences:
1. Overall similarity to closest match (name it, give %)
2. Which failure pattern is most applicable and why
3. What early warning would have changed outcome — does it exist now?
Reference company names. No generic advice.
```

**Output:**
```python
class ObituaryBotOutput(BaseModel):
    startup_id: UUID
    score: float                       # 0-100 (higher = more similar to failures)
    top_failure_pattern: str
    pattern_confidence: float
    similar_cases: list[SimilarCase]
    failure_taxonomy_breakdown: dict
    llm_diagnosis: str
    computed_at: datetime
```

**Kafka:** `startup.obituary.high_match` (score > 70) → no downstream triggers (terminal)
**API:** `GET /startup/{id}/obituary`, `GET /obituary/patterns`, `GET /obituary/corpus/stats`
**DAG:** Weekly Sunday 8am — scrape_new_postmortems → extract_structured → rebuild_faiss → run_obituary_bot
**Tests:** test_faiss_index_loaded, test_high_similarity_known_failure, test_low_similarity_healthy, test_pattern_extracted, test_similar_cases_named, test_corpus_coverage

---

## Bot 3 — TermBot

**File:** `startupintel/bots/term_bot.py`
**Purpose:** Decode any term sheet. Score founder-friendliness. Flag predatory clauses.
**Connectors:** sec_edgar.py (corpus), PyMuPDF (PDF parser) — on-demand, not scheduled

**12 clauses with weights:**
```python
CLAUSES = {
    "liquidation_preference": {"weight": 0.20, "red_flag": "multiplier > 1 OR participating", "standard": "1x non-participating"},
    "anti_dilution":          {"weight": 0.15, "red_flag": "full_ratchet", "standard": "broad_based_weighted_average"},
    "board_composition":      {"weight": 0.15, "red_flag": "investor_majority", "standard": "2F 2I 1 independent"},
    "option_pool_shuffle":    {"weight": 0.12, "red_flag": "pre_money_expansion", "standard": "post_money"},
    "drag_along":             {"weight": 0.10, "red_flag": "threshold < 50%", "standard": "majority common + majority preferred"},
    "vesting_schedule":       {"weight": 0.08, "red_flag": "no_acceleration OR cliff > 12mo", "standard": "4yr/1yr cliff, double trigger"},
    "pay_to_play":            {"weight": 0.07, "red_flag": "present without carveout", "standard": "absent or with founder carveout"},
    "pro_rata_rights":        {"weight": 0.05, "red_flag": "super_pro_rata", "standard": "standard pro_rata"},
    "information_rights":     {"weight": 0.03, "red_flag": "absent", "standard": "quarterly + annual audited"},
    "right_of_first_refusal": {"weight": 0.02, "red_flag": "right_of_first_offer", "standard": "standard ROFR"},
    "co_sale_rights":         {"weight": 0.02, "red_flag": "no founder carveout", "standard": "with founder carveout ≤10%"},
    "valuation_cap":          {"weight": 0.01, "red_flag": "cap < 3x last post-money", "standard": "context dependent"},
}
```

**Per-clause LLM extraction prompt:**
```
You are an expert startup lawyer. Return JSON only. No preamble.
Clause type: {clause_name}
Market standard: {market_standard}
Red flag condition: {red_flag_condition}
Relevant text: {clause_text}
Return: {
  "detected_value": str,
  "is_market_standard": bool,
  "risk_level": "low"|"medium"|"high",
  "explanation": "1 sentence",
  "founder_impact": "1 sentence"
}
```

**Scoring:** clause_score = {low:1.0, medium:0.5, high:0.0}[risk_level] per clause; weighted sum × 100

**Output:**
```python
class TermBotOutput(BaseModel):
    analysis_id: UUID
    startup_id: Optional[UUID]
    founder_friendliness_score: float
    market_benchmark_score: float
    red_flags: list[str]
    yellow_flags: list[str]
    clause_scores: dict[str, ClauseAnalysis]
    llm_diagnosis: str
    analyzed_at: datetime

class ClauseAnalysis(BaseModel):
    detected_value: str
    is_market_standard: bool
    risk_level: str
    explanation: str
    founder_impact: str
    weight: float
    score: float
```

**Kafka:** `termsheet.red_flag` (any clause risk_level=high) → no downstream triggers, alert only
**API:** `POST /termsheet` (PDF upload), `GET /termsheet/{id}`, `GET /termsheet/benchmark`
**DAG:** Monthly corpus refresh only — no scheduled bot run (on-demand via API)
**Tests:** test_founder_friendly_termsheet, test_predatory_termsheet, test_12_clauses_extracted, test_missing_clause_handled, test_benchmark_populated, test_pdf_parsed

---

## Bot 4 — PivotBot

**File:** `startupintel/bots/pivot_bot.py`
**Purpose:** Reconstruct actual pivot timeline from public signals before official narrative.
**Connectors:** wayback.py, producthunt.py, app_store.py, github.py, twitter.py, crunchbase.py

**Pivot detection logic:**
```python
# Wayback: cosine_sim(prev_snapshot, curr_snapshot) < 0.65 → pivot detected
# ProductHunt: multiple launches → each additional launch = pivot signal
# App Store: major_version_bump AND description_changed → pivot signal
# GitHub: repo_archived + new_repo_created within 60 days → tech pivot
# Twitter: quarterly keyword cosine_sim < 0.60 → positioning pivot
# Deduplicate: events within 30 days = same pivot event
```

**5 pivot types:**
```
customer_segment | product | revenue_model | technology | geography
```

**Scoring:**
```python
WEIGHTS = {
    "pivot_count_normalized": 0.50,    # min(1.0, pivot_count / 3)
    "avg_confidence": 0.30,            # mean confidence across detected pivots
    "recency": 0.20                    # recent pivots weighted higher
}
```

**LLM pivot type classification prompt:**
```
Classify the type of pivot based on these two website snapshots.
Before: {prev_snapshot_summary}
After: {curr_snapshot_summary}
Return JSON: {"pivot_type": "customer_segment|product|revenue_model|technology|geography",
              "evidence": "1 sentence explaining what changed"}
```

**Output:**
```python
class PivotBotOutput(BaseModel):
    startup_id: UUID
    score: float
    pivot_count: int
    pivot_events: list[PivotEvent]
    official_pivot_announced: Optional[datetime]
    detected_vs_announced_gap_days: Optional[int]
    primary_pivot_type: Optional[str]
    llm_narrative: str
    computed_at: datetime

class PivotEvent(BaseModel):
    date: datetime
    source: str
    pivot_type: str
    confidence: float
    evidence_summary: str
```

**Kafka:** `startup.pivot.detected` (new pivot since last run) → triggers ObituaryBot, PMFBot
**API:** `GET /startup/{id}/pivot`, `GET /startup/{id}/pivot/timeline`
**DAG:** Weekly Monday 9am — fetch_wayback_snapshots → run_pivot_bot → emit_pivot_events
**Tests:** test_known_pivot_detected, test_stable_startup_no_pivot, test_cosine_sim_computed, test_deduplication, test_gap_days_computed, test_pivot_type_valid

---

## Bot 5 — PMFBot

**File:** `startupintel/bots/pmf_bot.py`
**Purpose:** Detect PMF inflection points from 8 public signals before NPS surveys catch them.
**Connectors:** app_store.py, g2_capterra.py, pytrends, github.py, Stack Overflow API, Reddit PRAW, producthunt.py, twitter.py

**8 signals + weights:**
```python
WEIGHTS = {
    "app_store_review_velocity": 0.25,
    "g2_rating_trajectory": 0.20,
    "organic_search_growth": 0.20,
    "github_star_acceleration": 0.15,
    "stackoverflow_volume": 0.10,
    "reddit_mention_sentiment": 0.05,
    "producthunt_upvote_rate": 0.03,
    "twitter_mention_growth": 0.02
}
```

**Each signal normalized 0-1:** percentile vs. industry baseline for that signal type.

**Changepoint detection:**
```python
import ruptures as rpt
# PELT algorithm on rolling 90-day composite score window
# pen=10 sensitivity threshold
# changepoint detected if breakpoints has > 1 entry
```

**PMF thresholds:**
```python
PMF_STATUS = {(0,30): "pre_pmf", (31,60): "approaching", (61,80): "strong", (81,100): "clear"}
```

**Output:**
```python
class PMFBotOutput(BaseModel):
    startup_id: UUID
    score: float
    pmf_status: str
    signal_breakdown: dict[str, float]
    changepoint_detected: bool
    changepoint_date: Optional[datetime]
    days_ahead_of_nps_estimate: Optional[int]
    strongest_signal: str
    weakest_signal: str
    llm_diagnosis: str
    computed_at: datetime
```

**Kafka:** `startup.pmf.inflection` (changepoint OR score crosses 60) → triggers InvestorBot
**API:** `GET /startup/{id}/pmf`, `GET /startup/{id}/pmf/history`
**DAG:** Weekly Monday 7am — fetch_all_pmf_signals → run_pmf_bot → detect_changepoints
**Tests:** test_high_pmf_known_startup, test_pre_launch_low_pmf, test_changepoint_detected, test_no_changepoint_flat, test_all_8_signals_present, test_missing_signal_degraded

---

## Bot 6 — AcceleratorBot

**File:** `startupintel/bots/accelerator_bot.py`
**Purpose:** Rank 400+ accelerators by actual outcome ROI — not reputation.
**Connectors:** crunchbase.py, linkedin.py, data/accelerators_seed.csv

**7 metrics per accelerator:**
```python
METRICS = {
    "follow_on_funding_rate": 0.30,       # % cohort raised after demo day
    "median_time_to_series_a_months": 0.20, # inverted — faster = better
    "survival_rate_3yr": 0.20,
    "unicorn_rate": 0.15,
    "acqui_hire_rate": 0.10,
    "shutdown_rate": -0.05                # negative weight — penalized
}
```

**Normalization dimensions:** industry focus, geography, cohort vintage year, stage at entry.
**Minimum cohort size:** 10 companies — below threshold, excluded from rankings.
**Confidence interval:** Wilson score interval based on cohort size.

**Output:**
```python
class AcceleratorBotOutput(BaseModel):
    accelerator_id: UUID
    name: str
    roi_score: float
    global_rank: int
    industry_rank: int
    geo_rank: int
    raw_metrics: dict[str, float]
    normalized_metrics: dict[str, float]
    cohort_count: int
    cohort_companies_analyzed: int
    confidence_interval: tuple[float, float]
    peer_comparison: list[dict]
    computed_at: datetime
```

**No Kafka event** — slow-moving monthly data, no cross-bot triggers.
**API:** `GET /accelerator/rankings?industry=saas&stage=seed&geo=us`, `GET /accelerator/{id}`, `GET /accelerator/recommend?startup_stage=seed&industry=fintech&geo=us`
**DAG:** Monthly 1st of month — refresh_crunchbase_outcomes → compute_metrics → update_rankings → update_neo4j
**Tests:** test_yc_ranks_high, test_small_accelerator_ranks_low, test_industry_normalization, test_minimum_cohort_filter, test_confidence_interval_wider_small_cohort, test_recommend_by_profile

---

## Bot 7 — InvestorBot

**File:** `startupintel/bots/investor_bot.py`
**Purpose:** Score investors by network centrality — who opens doors vs. who just takes board seats.
**Connectors:** crunchbase.py, linkedin.py, twitter.py

**Graph construction:**
```python
import networkx as nx
# Step 1: bipartite graph — investors ↔ startups (from Crunchbase co-investments)
# Step 2: project to investor-investor graph (edge = shared portfolio company)
# Step 3: compute centrality metrics on projected graph
```

**4 centrality metrics + weights:**
```python
WEIGHTS = {
    "betweenness": 0.35,     # bridges disconnected investor clusters
    "eigenvector": 0.25,     # connected to other high-centrality investors
    "diversity": 0.20,       # Gini coefficient of portfolio industries/stages (inverted)
    "value_add_proxy": 0.20  # LinkedIn intro posts + Twitter engagement rate
}
```

**Value-add proxy:**
```python
# intro_count = count of public LinkedIn posts with "excited to announce [portfolio company]"
# twitter_engagement = avg like+retweet rate on portfolio company mentions
# value_add_proxy = min(1.0, (intro_count/50 + twitter_engagement) / 2)
```

**Output:**
```python
class InvestorBotOutput(BaseModel):
    investor_id: UUID
    name: str
    firm: str
    centrality_score: float
    global_rank: int
    betweenness_percentile: float
    eigenvector_percentile: float
    portfolio_diversity_score: float
    value_add_proxy_score: float
    portfolio_count: int
    notable_exits: list[str]
    network_visualization_data: dict    # D3 force graph payload
    computed_at: datetime
```

**Kafka:** `investor.network.updated` (centrality_score changes > 10 points) → no downstream triggers
**API:** `GET /investor/{id}`, `GET /investor/rankings?stage=series_a&industry=fintech`, `GET /investor/{id}/network`, `GET /investor/recommend?startup_stage=seed&industry=saas`
**DAG:** Weekly Sunday midnight — refresh_co_investment_graph → compute_centrality (NetworkX — allow 30min for large graph) → augment_engagement → update_scores → update_neo4j
**Tests:** test_sequoia_ranks_high, test_angel_ranks_low, test_betweenness_float, test_graph_projection_valid, test_diversity_gini, test_recommend_relevant

---

## Bot 8 — AcquiBot

**File:** `startupintel/bots/acqui_bot.py`
**Purpose:** Predict acqui-hire probability and identify likely acquirers.
**Connectors:** linkedin.py, github.py, crunchbase.py — depends on RunwayBot score as input feature

**Feature set:**
```python
FEATURES = {
    # Team (weight group: 0.30)
    "faang_alumni_ratio": "% team with FAANG experience",
    "top10_uni_ratio": "% team with top-10 university degree",
    "founder_prior_exit": "binary — any founder has prior exit",
    "avg_years_experience": "mean team YoE",
    # Tech (weight group: 0.25)
    "tech_stack_rarity_score": "rarity score of languages/frameworks",
    "personal_repo_stars": "sum of stars on team personal GitHub repos",
    # Network (weight group: 0.25)
    "investor_acquirer_overlap": "% of investors with portfolio at top-50 acquirers",
    "linkedin_connections_at_acquirers": "count of 1st-degree connections at top-50",
    # Financial (weight group: 0.20)
    "runway_stress_score": "RunwayBot score — upstream dependency",
    "months_since_last_raise": "float — higher = more likely"
}
```

**Model:** XGBoost binary classifier
```python
# Training: 500 confirmed acqui-hires + 500 controls from Crunchbase (2015-2021)
# Test: 2022-2024 holdout
# Model file: models/acqui_bot_xgb_v1.pkl
# Retrain: monthly via scripts/train_acqui_model.py
# SHAP values computed for every prediction (interpretability)
```

**Acquirer matching (top-50 acquirers list hardcoded: Google, Meta, Apple, Microsoft, Salesforce...):**
```python
# For each acquirer: fit_score = 0.4*tech_overlap + 0.35*team_fit + 0.25*network_overlap
# tech_overlap = cosine_sim(startup_stack_embedding, acquirer_past_acquisitions_stack)
# team_fit = cosine_sim(team_expertise_embedding, acquirer_hiring_focus)
# network_overlap = investor_acquirer_overlap score for this specific acquirer
```

**Output:**
```python
class AcquiBotOutput(BaseModel):
    startup_id: UUID
    acqui_probability: float            # 0-1 XGBoost output
    score: float                        # probability * 100
    feature_importances: dict[str, float]  # SHAP values
    likely_acquirers: list[AcquirerMatch]
    team_quality_score: float
    tech_rarity_score: float
    network_overlap_score: float
    runway_stress_input: float
    llm_narrative: str
    computed_at: datetime

class AcquirerMatch(BaseModel):
    acquirer_id: UUID
    name: str
    domain: str
    fit_score: float
    tech_overlap: float
    team_fit: float
    network_overlap: float
    rationale: str                      # LLM 1-sentence rationale
```

**Kafka:** `startup.acqui.signal` (probability > 0.60) → triggers InvestorBot
**API:** `GET /startup/{id}/acqui`, `GET /startup/{id}/acqui/acquirers`
**DAG:** Weekly Sunday 10am — refresh_team_profiles → ensure_runway_bot_ran → run_acqui_bot → monthly_retrain
**Tests:** test_high_team_raises_prob, test_low_team_lowers_prob, test_runway_stress_is_feature, test_5_acquirers_returned, test_shap_sum_to_1, test_tech_rarity_computed, test_model_loads

---

## Cross-Bot Kafka Event Pipeline (startupintel/events/topics.py)

```python
TOPICS = {
    "startup.stress.high": {
        "threshold": "runway_score > 65",
        "triggers": ["pivot_bot", "obituary_bot", "acqui_bot"]
    },
    "startup.pmf.inflection": {
        "threshold": "changepoint_detected OR score crosses 60",
        "triggers": ["investor_bot"]
    },
    "startup.pivot.detected": {
        "threshold": "new pivot event since last run",
        "triggers": ["obituary_bot", "pmf_bot"]
    },
    "startup.acqui.signal": {
        "threshold": "acqui_probability > 0.60",
        "triggers": ["investor_bot"]
    },
    "termsheet.red_flag": {
        "threshold": "any clause risk_level == high",
        "triggers": []            # alert only
    },
    "startup.obituary.high_match": {
        "threshold": "obituary_score > 70",
        "triggers": []            # terminal
    },
    "investor.network.updated": {
        "threshold": "centrality_score delta > 10",
        "triggers": []
    }
}
# All downstream bot runs are async (fire-and-forget). Never block original bot.run().
# After all triggered bots complete → synthesizer.generate_brief(startup_id)
```

---

## LLM Synthesizer (startupintel/llm/synthesizer.py)

```
SYNTHESIS_PROMPT:
Startup: {name} | {industry} | {stage}
- Runway stress: {runway_score}/100 — {runway_diagnosis}
- PMF score: {pmf_score}/100 — {pmf_status}
- Pivot count: {pivot_count} — last: {last_pivot_date}
- Failure similarity: {obituary_score}/100 — most similar: {top_failure_match}
- Acqui-hire probability: {acqui_probability}%

Write 4-paragraph intelligence brief:
1. Current state summary (2-3 sentences)
2. Biggest risk signal and why it matters now
3. Biggest opportunity signal and why it matters now
4. Recommended action for VC/founder/operator — specific, with timing

Tone: direct, analytical, no hedging. Decide today.
```

**API:** `GET /startup/{id}/brief` → runs synthesizer if all bot scores fresh, else uses cached scores

---

## Build Order (70 Days)

| Phase | Days | Deliverable |
|---|---|---|
| 1 — Infrastructure | 1–7 | docker-compose, all DB schemas, RAG, LLM client |
| 2 — RunwayBot | 8–14 | First bot end-to-end, API, DAG, 6 tests passing |
| 3 — ObituaryBot | 15–21 | Post-mortem corpus, FAISS index, cross-bot handler |
| 4 — TermBot | 22–26 | 12-clause extraction, PDF upload endpoint |
| 5 — PivotBot | 27–33 | Wayback + ProductHunt + App Store connectors |
| 6 — PMFBot | 34–40 | 8-signal aggregator, PELT changepoint |
| 7 — AcceleratorBot | 41–46 | ROI computation, leaderboard endpoint |
| 8 — InvestorBot | 47–53 | NetworkX centrality, D3 viz payload |
| 9 — AcquiBot | 54–60 | XGBoost model training, acquirer matching |
| 10 — Synthesis | 61–70 | Kafka pipeline, synthesizer, Slack bot, deploy |

---

## Non-Negotiable Rules for Codex

1. Read this file fully at start of every session.
2. Build `db/models.py` and migrate before any bot.
3. Every bot extends `BaseBot` — no exceptions.
4. Type hints everywhere. No bare `dict`. Use TypedDict or Pydantic.
5. All I/O is async — no blocking calls in event loop.
6. Graceful degradation: missing signal → log warning → score without it.
7. Redis cache: bot scores 1hr TTL, API data 24hr, embeddings disk-permanent.
8. RAG retrieval before every LLM call — no exceptions.
9. All tests in `test_{bot_name}.py` must pass before starting next bot.
10. Kafka events are fire-and-forget — never await downstream bots.
11. All weights come from `config.py` → `.env` — zero hardcoded floats.
12. Logging format: `{time} | {level} | {bot} | startup={id} | score={score} | latency={ms}ms`.

---

## First Commands

```bash
git clone ... && cd startupintel
cp .env.example .env
docker-compose up -d
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_database.py
pytest tests/ -v
```

**First file to write:** `startupintel/db/models.py`
Everything depends on the schema. Build it first. Migrate it. Then build.
