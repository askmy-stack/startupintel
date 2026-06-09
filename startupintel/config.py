from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = "postgresql+asyncpg://user:pass@localhost:5432/startupintel"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "your_password"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "startupintel-bots"

    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"

    embedding_model: str = "all-mpnet-base-v2"
    faiss_index_path: str = "./data/faiss_index"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me"

    runway_weight_headcount: float = Field(default=0.35, ge=0, le=1)
    runway_weight_job_postings: float = Field(default=0.25, ge=0, le=1)
    runway_weight_sentiment: float = Field(default=0.20, ge=0, le=1)
    runway_weight_domain: float = Field(default=0.10, ge=0, le=1)
    runway_weight_funding_recency: float = Field(default=0.10, ge=0, le=1)
    runway_high_stress_threshold: float = 65.0

    github_token: str | None = None
    twitter_bearer_token: str | None = None
    producthunt_token: str | None = None
    sec_edgar_user_agent: str = "StartupIntel contact@startupintel.io"
    app_store_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

