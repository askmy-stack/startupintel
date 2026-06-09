# StartupIntel — Code Review & Execution Plan

_Review of `main` plus all open branches/PRs. No code changes made; this is a planning document._

## 1. Where the project stands today

`main` is a clean **foundation** that does exactly what the README claims and nothing more:

- FastAPI app with `/health` and a demo `GET /startup/{id}/stress` (uses hardcoded `DEMO_SIGNALS`).
- `BaseBot` orchestration (cache → fetch → score → RAG → LLM → persist → graph → emit) and a working `RunwayBot` scoring core.
- Full SQLAlchemy models for the core schema, plus scaffold clients for Postgres/Neo4j/Redis.
- In-memory event producer, Null LLM client, empty RAG retriever (placeholders).
- 5 tests, `ruff` clean, CI green.

**Baseline health on `main`:** `ruff check .` passes, `pytest -q` → 5 passed. Good.

### The important finding: most of the "planned" work already exists, unmerged

| Branch / PR | State | What it contains |
|---|---|---|
| **PR #3 `production-ready`** | OPEN, mergeable, **CI failing** | The full platform: all 8 bots, 10 ingestion connectors, real Groq/Ollama LLM client, FAISS RAG, complete REST API + CRUD, JWT auth/orgs/API keys, Alembic migrations, Airflow DAGs, Kafka events, Slack, Prometheus, Elasticsearch, WebSockets, caching, k8s manifests, CI/CD, docs. ~+19.4k lines. |
| **PR #2 `codex/bots-working-foundation`** | DRAFT | Earlier/overlapping superset of the same work. |
| `runway`, `obituary`, `term`, `pivot`, `pmf`, `accelerator`, `investor`, `acqui` | branches (all point to the same commit) | Just the 7 remaining **bot scoring cores + tests** + `BOT_BUILD_PLANS.md`. ~+2.4k lines, isolated and reviewable. |

So the real question is **not "what to build next"** — a lot is built — but **"how to safely review, slim down, and land this work into `main` in reviewable increments."** A single 19k-line PR is effectively unreviewable and is currently red.

## 2. Concrete issues found

### Blocking / high priority
1. **PR #3 CI is red on lint** — `ruff check .` reports **156 errors**, mostly trivial `F401` (unused `datetime`/imports across all Airflow DAGs, alembic migration) and `F541` (f-strings without placeholders in `scripts/seed_database.py`). The `test` job dies at lint before tests run. Most are auto-fixable with `ruff check --fix`.
2. **19k-line mega-PR** is too large to review or merge safely. Needs to be decomposed.
3. **`alembic.ini` on `main` points at a non-existent `alembic/` dir** — migrations only exist on the unmerged branches. On `main`, schema creation relies on `Base.metadata.create_all` in `seed_database.py`, which is not production-safe.

### Security / config
4. **Insecure defaults** baked into `config.py`: `api_secret_key = "change-me"`, `neo4j_password = "your_password"`, Postgres `user:pass`. No startup-time validation that these were overridden in non-dev environments.
5. **No auth on `main`'s API** and (separately) **no CORS policy** — fine for a demo, but should be a conscious gate before any deployment. (Auth exists on PR #3; needs review.)
6. `Settings` uses `extra="ignore"`, so typos in `.env` keys silently do nothing.

### Correctness / design
7. **`BaseBot.run` caches the result keyed only by `name:startup_id`** with a fixed 1h TTL and no versioning — a bot logic/`version` change won't invalidate stale cached scores. Suggest including `version` in the cache key.
8. **`requirements.txt` duplicates `pyproject.toml`** and will drift. The Dockerfile installs from `requirements.txt` *then* `pip install -e .` — two sources of truth. Pick `pyproject` as canonical.
9. **Demo endpoint ships fake data** (`DEMO_SIGNALS`) with no marker that it's a stub; easy to mistake for real. `RunwayBot.fetch_signals` raises `NotImplementedError` on `main` (real wiring is on PR #3).
10. **`datetime`/timezone** is correct in models/base (`datetime.now(UTC)`), but the unmerged branches reintroduce naive `datetime.utcnow()` in places (PR #3 has a commit "datetime UTC fix" — verify it's complete).

### Quality / tooling
11. **Thin test coverage on `main`** (5 tests; no DB-layer, persistence, graph, or event-wiring tests; no `conftest.py`/fixtures even though `CLAUDE.md` references them).
12. **No pre-commit hooks**, no `mypy`/type-check in CI (despite `py.typed`-style typed code), no coverage gating.
13. CI runs only on Python 3.11 though `requires-python = ">=3.11"` — consider a 3.11/3.12 matrix.
14. **No structured logging, request-id, or error-handling middleware** on `main` (present on PR #3 — worth landing early as it's low-risk and high-value).

## 3. Recommended execution plan

### Phase 0 — Stabilize what's in review (days, not weeks)
- [ ] **Green PR #3's CI**: run `ruff check --fix .`, fix the residual `F541`/`F401`, get `pytest` actually executing and passing. (Quick win — unblocks any review.)
- [ ] Decide the integration strategy (recommended below) so the mega-PR stops growing.

### Phase 1 — Land the bot cores (low risk, high signal)
The 8 bot branches are small, self-contained, and test-backed. Merge these into `main` **first**, one reviewable PR each (or one combined "7 remaining bot scoring cores" PR):
- [ ] `obituary`, `term`, `pivot`, `pmf`, `accelerator`, `investor`, `acqui` scoring cores + their tests + `scoring/normalizer.py` additions.
- [ ] Add `BOT_BUILD_PLANS.md` to `main` as the canonical roadmap.
- This makes `main` match the README's "8 bots" promise with minimal infra risk.

### Phase 2 — Decompose PR #3 into reviewable slices
Carve the `production-ready` branch into themed PRs, each green on CI, roughly in dependency order:
1. [ ] **Migrations**: add `alembic/` env + initial migration so `alembic.ini` is real; stop relying on `create_all`.
2. [ ] **Ingestion connectors** (Crunchbase, GitHub, LinkedIn, Twitter, ProductHunt, SEC EDGAR, Wayback, WHOIS, App Store, Job Boards) with graceful-degradation tests + optional-dep fallbacks.
3. [ ] **Real LLM client (Groq+Ollama) + FAISS RAG retriever**, behind the existing `Null`/`Empty` interfaces so tests stay hermetic.
4. [ ] **RunwayBot real signal fetching** wired to connectors + DB (replace `DEMO_SIGNALS`).
5. [ ] **Full REST API / CRUD + per-bot routes** + Pydantic schemas + OpenAPI examples.
6. [ ] **Cross-cutting hardening**: structured logging, request-id middleware, error handling, CORS, rate limiting, graceful shutdown. (Low-risk; could even precede #5.)
7. [ ] **Auth & multi-tenant**: JWT, organizations, API keys, RBAC — needs careful security review.
8. [ ] **Events/workers**: Kafka producer/consumer + handlers replacing the in-memory producer.
9. [ ] **Airflow DAG bodies** + `weekly_digest`.
10. [ ] **Slack integration** + unified brief synthesis.
11. [ ] **Ops**: Dockerfile/compose hardening, k8s manifests, Prometheus/Grafana, CI/CD, optional Elasticsearch.

### Phase 3 — Quality gates (do alongside, not after)
- [ ] Add `conftest.py` + fixtures (`sample_startups.json`, `sample_signals.json`); raise coverage on DB persistence, graph writes, event emission, and each bot.
- [ ] Add `pre-commit` (`ruff`, `ruff format`, end-of-file/whitespace) and `pre-commit install`.
- [ ] Add `mypy` + coverage threshold to CI; add a 3.11/3.12 matrix.
- [ ] Make `pyproject.toml` the single dependency source; have the Dockerfile install the package (drop the duplicate `requirements.txt` or generate it).
- [ ] Enforce config safety: fail fast if `api_secret_key`/DB/Neo4j creds are still defaults outside dev; switch `Settings` to `extra="forbid"` (or warn).
- [ ] Version-aware bot cache key (`name:version:startup_id`).

## 4. Suggested first action
If you want momentum: I can open a small PR that **fixes PR #3's 156 lint errors** (mostly `ruff --fix`) to get its CI green, and/or start **Phase 1** by merging the 7 bot scoring cores into `main` as a clean, test-backed PR. Tell me which and I'll proceed.
