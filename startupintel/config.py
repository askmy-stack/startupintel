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
    elasticsearch_url: str | None = None

    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    llm_timeout: float = 60.0

    embedding_model: str = "all-mpnet-base-v2"
    faiss_index_path: str = "./data/faiss_index"
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7

    crunchbase_api_key: str | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

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
    linkedin_email: str | None = None
    linkedin_password: str | None = None

    slack_bot_token: str | None = None
    slack_app_token: str | None = None
    slack_digest_channel: str = "#startupintel"

    email_from_address: str = "noreply@startupintel.io"
    sendgrid_api_key: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    storage_provider: Literal["local", "s3", "minio"] = "local"
    storage_local_path: str = "./data/uploads"
    storage_bucket: str = "startupintel-files"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    max_upload_size_mb: int = 50
    allowed_file_types: str = ".pdf,.doc,.docx,.txt,.csv,.json,.jpg,.jpeg,.png"

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
