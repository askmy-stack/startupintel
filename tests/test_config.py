import pytest

from startupintel.config import Settings


def test_development_allows_insecure_defaults():
    settings = Settings(environment="development")
    assert settings.api_secret_key == "change-me"


def test_production_rejects_insecure_defaults():
    with pytest.raises(ValueError, match="Insecure default"):
        Settings(environment="production")


def test_production_accepts_overridden_secrets():
    settings = Settings(
        environment="production",
        api_secret_key="a-real-secret",
        neo4j_password="a-real-password",
    )
    assert settings.environment == "production"
