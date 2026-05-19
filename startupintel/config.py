from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database & Storage
    postgres_url: str = "postgresql+asyncpg://user:pass@localhost:5432/startupintel"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "your_password"
    redis_url: str = "redis://localhost:6379/0"

    # Event Streaming
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "startupintel-bots"

    # LLM Configuration
    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    llm_timeout: float = 60.0
    llm_max_retries: int = 3

    # Embeddings & RAG
    embedding_model: str = "all-mpnet-base-v2"
    faiss_index_path: str = "./data/faiss_index"
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me"
    api_access_token_expire_minutes: int = 30

    # ========== RUNWAY BOT ==========
    runway_weight_headcount: float = Field(default=0.35, ge=0, le=1)
    runway_weight_job_postings: float = Field(default=0.25, ge=0, le=1)
    runway_weight_sentiment: float = Field(default=0.20, ge=0, le=1)
    runway_weight_domain: float = Field(default=0.10, ge=0, le=1)
    runway_weight_funding_recency: float = Field(default=0.10, ge=0, le=1)
    runway_high_stress_threshold: float = 65.0

    # ========== OBITUARY BOT ==========
    obituary_weight_top_match: float = Field(default=0.50, ge=0, le=1)
    obituary_weight_avg_top3: float = Field(default=0.30, ge=0, le=1)
    obituary_weight_cause_concentration: float = Field(default=0.20, ge=0, le=1)
    obituary_high_match_threshold: float = 70.0

    # ========== PMF BOT ==========
    pmf_weight_reviews: float = Field(default=0.25, ge=0, le=1)
    pmf_weight_g2: float = Field(default=0.20, ge=0, le=1)
    pmf_weight_search: float = Field(default=0.20, ge=0, le=1)
    pmf_weight_github: float = Field(default=0.15, ge=0, le=1)
    pmf_weight_stackoverflow: float = Field(default=0.10, ge=0, le=1)
    pmf_weight_reddit: float = Field(default=0.05, ge=0, le=1)
    pmf_weight_producthunt: float = Field(default=0.03, ge=0, le=1)
    pmf_weight_twitter: float = Field(default=0.02, ge=0, le=1)
    pmf_inflection_threshold: float = 60.0

    # ========== PIVOT BOT ==========
    pivot_weight_count: float = Field(default=0.50, ge=0, le=1)
    pivot_weight_confidence: float = Field(default=0.30, ge=0, le=1)
    pivot_weight_recency: float = Field(default=0.20, ge=0, le=1)

    # ========== ACQUI BOT ==========
    acqui_weight_team: float = Field(default=0.30, ge=0, le=1)
    acqui_weight_tech: float = Field(default=0.25, ge=0, le=1)
    acqui_weight_network: float = Field(default=0.25, ge=0, le=1)
    acqui_weight_financial: float = Field(default=0.20, ge=0, le=1)
    acqui_high_probability_threshold: float = 60.0

    # ========== INVESTOR BOT ==========
    investor_weight_betweenness: float = Field(default=0.35, ge=0, le=1)
    investor_weight_eigenvector: float = Field(default=0.25, ge=0, le=1)
    investor_weight_diversity: float = Field(default=0.20, ge=0, le=1)
    investor_weight_value_add: float = Field(default=0.20, ge=0, le=1)

    # ========== ACCELERATOR BOT ==========
    accel_min_cohort_size: int = 10

    # ========== EXTERNAL API KEYS ==========
    crunchbase_api_key: str | None = None
    github_token: str | None = None
    twitter_bearer_token: str | None = None
    producthunt_token: str | None = None
    linkedin_email: str | None = None
    linkedin_password: str | None = None
    sec_edgar_user_agent: str = "StartupIntel contact@startupintel.io"
    app_store_api_key: str | None = None

    # ========== SLACK INTEGRATION ==========
    slack_bot_token: str | None = None
    slack_app_token: str | None = None
    slack_digest_channel: str = "#startupintel"

    # ========== CACHE & RATE LIMITING ==========
    cache_ttl_seconds: int = 3600
    rate_limit_requests_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

