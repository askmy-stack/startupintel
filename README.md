# StartupIntel

**Eight ML bots. One platform. Every signal a startup emits, analyzed.**

StartupIntel ingests public signals — funding, headcount, pivot history, term sheets, PMF trajectory, investor networks — and unifies them into a single intelligence layer with cross-bot reasoning.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-blue.svg)](https://neo4j.com)

---

## The Problem

Understanding a startup today means:

- Manually checking Crunchbase for funding history
- Scrolling LinkedIn to estimate headcount trajectory
- Reading Medium post-mortems to find comparable failures
- Decoding term sheet legalese without a lawyer
- Guessing which investors actually open doors

All manual. All slow. All disconnected. A VC analyst spends 4+ hours per deal on signals that are publicly available and automatable.

**StartupIntel connects these signals. One platform. Eight bots. Real-time.**

---

## The Eight Bots

| # | Bot | Purpose | Output |
|---|---|---|---|
| 1 | **RunwayBot** | Detects financial stress 60–90 days before announcement | Runway stress score (0–100) + 5-signal breakdown |
| 2 | **ObituaryBot** | Mines 3,000+ post-mortems for failure patterns | Failure similarity score + top-3 historical matches |
| 3 | **TermBot** | Decodes term sheets clause by clause | Founder-friendliness score (0–100) + red flag list |
| 4 | **PivotBot** | Reconstructs actual pivot timeline from public signals | Pivot count + timeline + detected-vs-announced gap |
| 5 | **PMFBot** | Aggregates 8 public signals for PMF inflection detection | PMF score (0–100) + changepoint date |
| 6 | **AcceleratorBot** | Ranks 400+ accelerators by actual outcome ROI | ROI-adjusted leaderboard + best-fit recommender |
| 7 | **InvestorBot** | Scores investors by bridging network centrality | Value-add score + D3 network visualization |
| 8 | **AcquiBot** | Predicts acqui-hire probability + identifies acquirers | Acqui probability + ranked acquirer shortlist |

---

## What Makes This a Platform

Every bot writes signals into a shared Neo4j knowledge graph. The bots trigger each other via Kafka.

```
RunwayBot detects stress (score: 78)
  → PivotBot  →  homepage changed 3x in 60 days
  → ObituaryBot  →  67% similar to Quibi pre-shutdown
  → AcquiBot  →  Google acquisition probability: 34%
  → LLM synthesizer generates unified intelligence brief
```

One signal compounds into five. That is the moat.

---

## Bot Details

### Bot 1 — RunwayBot

Detects startup financial stress 60–90 days before public announcement.

**5 signals:**
| Signal | Weight | Source |
|---|---|---|
| Headcount 30-day delta | 35% | LinkedIn |
| Job posting 30-day delta | 25% | Job boards |
| Founder Twitter sentiment | 20% | Twitter |
| Domain renewal status | 10% | WHOIS |
| Days since last funding | 10% | Crunchbase |

**Risk levels:** 0–25 low · 26–50 monitor · 51–75 elevated · 76–100 high risk

**Kafka event:** `startup.stress.high` (score > 65) → triggers PivotBot, ObituaryBot, AcquiBot

**API:** `GET /startup/{id}/stress`

**DAG:** Daily 6am UTC

---

### Bot 2 — ObituaryBot

Mines 3,000+ startup post-mortems. Matches any startup against historical failures using semantic similarity.

**12-category failure taxonomy:**
```
no_market_need | ran_out_of_cash | wrong_team | competition |
pricing_model | poor_product | bad_timing | pivot_failure |
legal_regulatory | burnout | failed_to_raise | founder_conflict
```

**Pipeline:** Raw post-mortem text → LLM structured extraction → BERTopic clustering → FAISS index → cosine similarity scoring

**Scoring:** 50% top-match similarity + 30% avg top-3 similarity + 20% cause concentration

**Kafka event:** `startup.obituary.high_match` (score > 70) → terminal, no downstream

**API:** `GET /startup/{id}/obituary` · `GET /obituary/patterns` · `GET /obituary/corpus/stats`

**DAG:** Weekly Sunday 8am

---

### Bot 3 — TermBot

Decodes any term sheet PDF. Analyzes 12 clauses against NVCA standard terms. Flags predatory clauses.

**12 clauses analyzed with weights:**
| Clause | Weight | Red Flag Condition |
|---|---|---|
| Liquidation preference | 20% | Multiplier > 1x OR participating |
| Anti-dilution | 15% | Full ratchet |
| Board composition | 15% | Investor majority |
| Option pool shuffle | 12% | Pre-money expansion |
| Drag-along | 10% | Threshold < 50% |
| Vesting schedule | 8% | No acceleration OR cliff > 12mo |
| Pay-to-play | 7% | Present without founder carveout |
| Pro-rata rights | 5% | Super pro-rata |
| Information rights | 3% | Absent |
| ROFR | 2% | Right of first offer (stronger) |
| Co-sale rights | 2% | No founder carveout |
| Valuation cap | 1% | Cap < 3x last post-money |

**Scoring:** Each clause scored low(1.0) / medium(0.5) / high(0.0) · weighted sum × 100

**Kafka event:** `termsheet.red_flag` (any high-risk clause) → alert only

**API:** `POST /termsheet` (PDF upload) · `GET /termsheet/{id}` · `GET /termsheet/benchmark`

**DAG:** On-demand only (no scheduled run)

---

### Bot 4 — PivotBot

Reconstructs actual pivot timeline from 6 public signal sources — before the official narrative.

**6 signal sources:**
| Source | Detection method |
|---|---|
| Wayback Machine | cosine_sim between homepage snapshots < 0.65 = pivot |
| ProductHunt | Multiple launches = multiple product bets |
| App Store | Major version bump + description change |
| GitHub | Repo archived + new repo created within 60 days |
| Twitter | Quarterly keyword cosine_sim < 0.60 |
| Crunchbase | Description change history |

**5 pivot types:** customer_segment · product · revenue_model · technology · geography

**Deduplication:** Events within 30 days = same pivot event

**Kafka event:** `startup.pivot.detected` (new pivot since last run) → triggers ObituaryBot, PMFBot

**API:** `GET /startup/{id}/pivot` · `GET /startup/{id}/pivot/timeline`

**DAG:** Weekly Monday 9am

---

### Bot 5 — PMFBot

Aggregates 8 public signals to detect PMF inflection points — before NPS surveys catch them.

**8 signals:**
| Signal | Weight | Source |
|---|---|---|
| App Store review velocity | 25% | App Store / Play Store |
| G2/Capterra rating trajectory | 20% | G2, Capterra |
| Organic search growth | 20% | Google Trends (pytrends) |
| GitHub star acceleration | 15% | GitHub API |
| Stack Overflow question volume | 10% | Stack Overflow API |
| Reddit mention sentiment | 5% | Reddit PRAW |
| ProductHunt upvote rate | 3% | ProductHunt API |
| Twitter mention growth | 2% | Twitter API |

**Changepoint detection:** PELT algorithm (ruptures library) on rolling 90-day composite score window

**PMF status:**
- 0–30: Pre-PMF — don't scale
- 31–60: Approaching — watch closely
- 61–80: Strong — consider scaling
- 81–100: Clear PMF — scale now

**Kafka event:** `startup.pmf.inflection` (changepoint OR score crosses 60) → triggers InvestorBot

**API:** `GET /startup/{id}/pmf` · `GET /startup/{id}/pmf/history`

**DAG:** Weekly Monday 7am

---

### Bot 6 — AcceleratorBot

Ranks 400+ accelerators by actual outcome ROI — not reputation, not brand.

**7 metrics per accelerator:**
| Metric | Weight |
|---|---|
| Follow-on funding rate | 30% |
| Median time to Series A (inverted) | 20% |
| 3-year survival rate | 20% |
| Unicorn rate | 15% |
| Acqui-hire rate | 10% |
| Shutdown rate (penalized) | −5% |

**Normalization:** Adjusted for industry focus, geography, cohort vintage year, stage at entry.

**Minimum threshold:** 10 cohort companies required for inclusion in rankings.

**No Kafka event** — monthly data, no cross-bot triggers.

**API:** `GET /accelerator/rankings?industry=saas&stage=seed&geo=us` · `GET /accelerator/{id}` · `GET /accelerator/recommend`

**DAG:** Monthly 1st of month

---

### Bot 7 — InvestorBot

Scores investors by bridging network centrality — who actually opens doors vs. who just takes board seats.

**Graph construction:**
1. Bipartite graph: investors ↔ startups (Crunchbase co-investments)
2. Project to investor-investor graph (edge = shared portfolio company)
3. Compute NetworkX centrality metrics

**4 metrics:**
| Metric | Weight | Description |
|---|---|---|
| Betweenness centrality | 35% | Bridges disconnected investor clusters |
| Eigenvector centrality | 25% | Connected to other high-centrality investors |
| Portfolio diversity (Gini) | 20% | Diversity of stage, industry, geography |
| Value-add proxy | 20% | LinkedIn intro posts + Twitter engagement rate |

**Kafka event:** `investor.network.updated` (score delta > 10) → no downstream triggers

**API:** `GET /investor/{id}` · `GET /investor/rankings` · `GET /investor/{id}/network` · `GET /investor/recommend`

**DAG:** Weekly Sunday midnight

---

### Bot 8 — AcquiBot

Predicts acqui-hire probability using XGBoost trained on 500+ confirmed acqui-hires. Identifies likely acquirers.

**Feature groups:**
| Group | Weight | Features |
|---|---|---|
| Team quality | 30% | FAANG ratio, top-10 uni ratio, prior exits, avg YoE |
| Tech signals | 25% | Stack rarity score, personal repo stars |
| Network signals | 25% | Investor-acquirer overlap, LinkedIn connections at acquirers |
| Financial signals | 20% | RunwayBot score (upstream input), months since last raise |

**Model:** XGBoost binary classifier trained on Crunchbase 2015–2021, tested 2022–2024.

**Acquirer matching:** For each of 50 top acquirers, fit_score = 0.4×tech_overlap + 0.35×team_fit + 0.25×network_overlap

**SHAP values:** Computed for every prediction — interpretability built in.

**Kafka event:** `startup.acqui.signal` (probability > 0.60) → triggers InvestorBot

**API:** `GET /startup/{id}/acqui` · `GET /startup/{id}/acqui/acquirers`

**DAG:** Weekly Sunday 10am + monthly model retraining

---

## Cross-Bot Signal Flow

```
startup.stress.high (RunwayBot > 65)
  → PivotBot · ObituaryBot · AcquiBot

startup.pmf.inflection (PMFBot changepoint)
  → InvestorBot

startup.pivot.detected (PivotBot new pivot)
  → ObituaryBot · PMFBot

startup.acqui.signal (AcquiBot > 60%)
  → InvestorBot

termsheet.red_flag (TermBot high-risk clause)
  → alert only

startup.obituary.high_match (ObituaryBot > 70)
  → terminal

investor.network.updated (InvestorBot delta > 10)
  → no triggers
```

All cross-bot runs are async (fire-and-forget). After all triggered bots complete, the LLM synthesizer generates a unified brief.

---

## LLM Synthesizer

After cross-bot pipeline completes, the synthesizer generates a unified brief per startup:

```
4-paragraph structure:
1. Current state summary
2. Biggest risk signal + why it matters now
3. Biggest opportunity signal + why it matters now
4. Recommended action for VC/founder/operator — specific timing
```

**API:** `GET /startup/{id}/brief`

---

## Quickstart

```bash
git clone https://github.com/askmy-stack/startupintel
cd startupintel
cp .env.example .env      # add your API keys
docker-compose up -d
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_database.py
uvicorn startupintel.api.main:app --reload
```

Demo API mode (no API keys needed):
```bash
uvicorn startupintel.api.main:app --reload
curl http://localhost:8000/startup/00000000-0000-0000-0000-000000000001/stress
# Returns RunwayBot output from synthetic demo signals.
```

## Current Implementation Status

This first version is a working foundation, not the full intelligence platform yet.

Shipped now:
- FastAPI app with `/health` and demo `/startup/{id}/stress`
- SQLAlchemy async models for the core PostgreSQL schema
- Config loading from `.env`
- RunwayBot scoring, risk levels, and high-stress event emission
- Neo4j schema helpers, Redis/Postgres/Neo4j clients, and test-friendly event producer
- Docker, Compose, package metadata, seed script, linting, and tests

Planned next:
- Real connector implementations for Crunchbase, LinkedIn, GitHub, Twitter, ProductHunt, SEC EDGAR, and WHOIS
- ObituaryBot RAG corpus/indexing, TermBot PDF clause analysis, and the remaining six bot implementations
- Kafka consumers/producers, Airflow DAGs, Slack digest, and unified LLM synthesizer

---

## Full API Reference

```
# Startup intelligence
GET  /startup/{id}                    → All bot scores + metadata
GET  /startup/{id}/stress             → RunwayBot output
GET  /startup/{id}/obituary           → ObituaryBot output
GET  /startup/{id}/pivot              → PivotBot output
GET  /startup/{id}/pivot/timeline     → Pivot events sorted by date
GET  /startup/{id}/pmf                → PMFBot output
GET  /startup/{id}/pmf/history        → Historical PMF scores
GET  /startup/{id}/acqui              → AcquiBot output
GET  /startup/{id}/acqui/acquirers    → Ranked acquirer shortlist
GET  /startup/{id}/brief              → LLM unified brief (synthesizer)
POST /startup/search                  → Search by name, domain, industry, stage

# Term sheet
POST /termsheet                       → Upload PDF → full analysis
GET  /termsheet/{id}                  → Retrieve past analysis
GET  /termsheet/benchmark             → Market standard scores by stage

# Accelerator
GET  /accelerator/rankings            → AcceleratorBot leaderboard
GET  /accelerator/{id}                → Single accelerator profile
GET  /accelerator/recommend           → Best-fit accelerators for a startup profile

# Investor
GET  /investor/{id}                   → InvestorBot output
GET  /investor/rankings               → Centrality leaderboard
GET  /investor/{id}/network           → D3 network visualization data
GET  /investor/recommend              → Best-fit investors for a startup profile

# System
GET  /obituary/patterns               → Failure taxonomy with cluster counts
GET  /obituary/corpus/stats           → Corpus size + last updated
GET  /bots/status                     → All bot last-run times + health
GET  /health                          → API health check
```

Full interactive docs at `http://localhost:8000/docs`

---

## Architecture

```
Data Sources
  Crunchbase · LinkedIn · GitHub · SEC EDGAR
  Wayback Machine · App Store · ProductHunt · Twitter
         │
         │  Apache Airflow (scheduled ingestion)
         ▼
Storage Layer
  PostgreSQL (signals + scores)
  Neo4j (relationship graph)
  Redis (cache + task queue)
  FAISS (RAG vector index)
         │
         ▼
Intelligence Layer
  8 Bots · LLM (Groq/Ollama) · RAG (FAISS) · Kafka Events
         │
         ▼
Product Surface
  FastAPI REST · React Dashboard · Slack Digest Bot
```

---

## Data Sources

| Source | Data captured | Bot(s) |
|---|---|---|
| Crunchbase API | Funding, exits, acquisitions, co-investments | All |
| LinkedIn (Playwright) | Headcount snapshots, role changes, team profiles | RunwayBot, InvestorBot, AcquiBot |
| GitHub API | Stars, commits, contributors, repo events | PMFBot, PivotBot, AcquiBot |
| SEC EDGAR API | Term sheets, S-1 filings | TermBot |
| Wayback Machine | Homepage snapshots at 6-month intervals | PivotBot |
| App Store / Play Store | Review velocity, version history | PMFBot, PivotBot |
| ProductHunt API | Launches, upvotes, comments | PMFBot, PivotBot |
| Twitter API | Founder sentiment, mention growth | RunwayBot, PivotBot, PMFBot |
| Job boards (Indeed + LinkedIn) | Posting count changes | RunwayBot |
| WHOIS | Domain renewal dates | RunwayBot |
| G2 / Capterra | Rating trajectory | PMFBot |

---

## Dataset Release

**StartupIntel Failure Corpus v1.0** — 1,000+ labeled startup post-mortems

Each entry includes: startup name, primary + secondary failure cause (12-category taxonomy), stage at death, industry, team size, runway at death, source URL, date.

Available on HuggingFace: `huggingface.co/datasets/startupintel/failure-corpus`

---

## Research Papers

| Title | Bot | Target |
|---|---|---|
| Multi-signal startup financial distress detection: a 60–90 day leading indicator framework | RunwayBot | EMNLP Industry Track |
| Taxonomizing startup failure: NLP analysis of 3,000 post-mortems | ObituaryBot | ACL System Demos |
| Public signal proxies for product-market fit: which metrics lead NPS? | PMFBot | KDD Applied Data Science |
| Investor value-add via network centrality: beyond capital in startup ecosystems | InvestorBot | ACM WebSci |

---

## Benchmarks

| Bot | Metric | Target | Baseline |
|---|---|---|---|
| RunwayBot | Precision@60d on 200 shutdowns | > 70% | Random: 12% |
| ObituaryBot | Cluster silhouette score | > 0.45 | LDA: 0.31 |
| PMFBot | Days ahead of NPS signal | > 14 days | Direct NPS: 0 |
| AcquiBot | AUC-ROC holdout 2022-2024 | > 0.75 | Logistic: 0.61 |
| TermBot | Clause classification accuracy | > 85% | Keyword match: 54% |

---

## Build Order

| Phase | Days | Ships |
|---|---|---|
| 1 — Infrastructure | 1–7 | docker-compose, all schemas, RAG, LLM client |
| 2 — RunwayBot | 8–14 | First bot, API, DAG, 6 tests |
| 3 — ObituaryBot | 15–21 | Post-mortem corpus, FAISS, cross-bot handler |
| 4 — TermBot | 22–26 | 12-clause analysis, PDF upload |
| 5 — PivotBot | 27–33 | 6-source pivot detection |
| 6 — PMFBot | 34–40 | 8-signal aggregator, PELT changepoint |
| 7 — AcceleratorBot | 41–46 | ROI ranking, leaderboard |
| 8 — InvestorBot | 47–53 | NetworkX centrality, D3 payload |
| 9 — AcquiBot | 54–60 | XGBoost model, acquirer matching |
| 10 — Synthesis | 61–70 | Kafka pipeline, synthesizer, Slack, deploy |

---

## Contributing

```bash
pip install -e ".[dev]"
pytest tests/ -v

# Before submitting PR:
# 1. All tests pass
# 2. New bot has test file with minimum 6 tests
# 3. New endpoint has Pydantic schema in api/schemas.py
# 4. Bot weights documented in README and configurable via .env
```

Good first issues:
- Add a new data source connector (extend `ingestion/base.py`)
- Improve TermBot clause extraction prompts
- Add a new PMFBot signal
- Expand ObituaryBot corpus scraper coverage

---

## License

MIT — use it, fork it, build on it.

---

Built by [Abhinaysai Kamineni](https://linkedin.com/in/abhinaysai-kamineni) · MS Data Science, GWU

*Not affiliated with Crunchbase, LinkedIn, or any data source.*
