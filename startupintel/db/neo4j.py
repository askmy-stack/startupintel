from neo4j import AsyncDriver, AsyncGraphDatabase

from startupintel.config import get_settings


def get_neo4j_driver() -> AsyncDriver:
    settings = get_settings()
    return AsyncGraphDatabase.driver(
        settings.neo4j_url,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

