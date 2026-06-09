from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Insecure defaults that must be overridden outside development.
INSECURE_DEFAULTS = {
    "neo4j_password": "your_password",
    "api_secret_key": "change-me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"

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

    @model_validator(mode="after")
    def _reject_insecure_defaults(self) -> "Settings":
        if self.environment == "development":
            return self
        offenders = [
            name for name, insecure in INSECURE_DEFAULTS.items() if getattr(self, name) == insecure
        ]
        if offenders:
            raise ValueError(
                f"Insecure default value(s) for {', '.join(offenders)} are not allowed "
                f"when ENVIRONMENT={self.environment}. Set them in the environment."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
