# Contributing to StartupIntel

Thank you for your interest in contributing to StartupIntel! This document provides guidelines and information to help you contribute effectively.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect privacy and security concerns

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Neo4j 5.x
- Redis 7
- Docker & Docker Compose (optional but recommended)

### Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/startupintel.git
   cd startupintel
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

5. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Start infrastructure services:
   ```bash
   docker compose up -d postgres neo4j redis
   ```

7. Run database migrations:
   ```bash
   alembic upgrade head
   ```

8. Seed sample data (optional):
   ```bash
   python scripts/seed_database.py
   ```

## Development Workflow

### Branch Naming

Use descriptive branch names with the following prefixes:

- `feature/` - New features or enhancements
- `bugfix/` - Bug fixes
- `hotfix/` - Critical production fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring without feature changes

Example: `feature/add-email-notifications`

### Making Changes

1. Create a new branch from `main`:
   ```bash
   git switch main
   git pull origin main
   git switch -c feature/your-feature-name
   ```

2. Make your changes with clear, focused commits

3. Write or update tests as needed

4. Ensure all tests pass:
   ```bash
   pytest -q
   ```

5. Run linting and type checking:
   ```bash
   ruff check .
   mypy startupintel
   ```

6. Format code if needed:
   ```bash
   ruff format .
   ```

## Project Structure

```
startupintel/
├── api/                    # FastAPI application
│   ├── dependencies/       # FastAPI dependencies (auth, db, etc.)
│   ├── routes/             # API route handlers
│   ├── schemas/            # Pydantic models
│   └── main.py             # Application entry point
├── bots/                   # Bot implementations
│   ├── base.py             # BaseBot abstract class
│   ├── runway_bot.py       # RunwayBot implementation
│   └── ...                 # Other bot implementations
├── db/                     # Database layer
│   ├── models.py           # SQLAlchemy models
│   ├── postgres.py         # PostgreSQL connection
│   ├── neo4j.py            # Neo4j connection
│   └── redis.py            # Redis connection
├── events/                 # Event streaming
│   ├── producer.py         # Event producer
│   └── topics.py           # Event topic definitions
├── ingestion/              # Data ingestion connectors
│   ├── crunchbase.py       # Crunchbase connector
│   ├── github.py           # GitHub connector
│   └── ...                 # Other connectors
├── llm/                    # LLM client abstractions
│   ├── client.py           # Unified LLM client
│   └── prompts.py          # Prompt templates
├── rag/                    # Retrieval-Augmented Generation
│   ├── retriever.py        # Document retriever
│   └── embeddings.py       # Embedding utilities
├── utils/                  # Shared utilities
│   ├── auth.py             # Authentication utilities
│   ├── cache.py            # Caching utilities
│   ├── circuit_breaker.py  # Circuit breaker pattern
│   ├── elasticsearch.py    # Elasticsearch client
│   ├── feature_flags.py    # Feature flag system
│   ├── logging_config.py   # Structured logging
│   ├── notifications.py    # Email/Slack notifications
│   ├── retry.py            # Retry logic
│   └── storage.py          # File storage backends
├── config.py               # Application configuration
├── tests/                  # Test suite
│   ├── test_api/           # API tests
│   ├── test_bots/          # Bot tests
│   └── conftest.py         # Test fixtures
├── scripts/                # Utility scripts
│   └── seed_database.py    # Database seeding
├── docs/                   # Documentation
│   ├── BOT_BUILD_PLANS.md
│   └── BOT_QA_GUIDE.md
├── docker-compose.yml      # Development infrastructure
├── Dockerfile              # Production image
├── k8s/                    # Kubernetes manifests
├── .github/workflows/      # CI/CD workflows
└── README.md               # Project overview
```

## Coding Standards

### Python Style

- Follow PEP 8 with these additions:
  - Line length: 100 characters maximum
  - Use type hints for all function signatures
  - Use descriptive variable names
  - Add docstrings to all public functions and classes

### Type Hints

Always use type hints:

```python
from typing import Optional, List

def process_startup(
    startup_id: UUID,
    signals: List[Signal],
    config: Optional[Config] = None
) -> AnalysisResult:
    """Process startup signals and return analysis.
    
    Args:
        startup_id: Unique startup identifier
        signals: List of signals to process
        config: Optional processing configuration
        
    Returns:
        AnalysisResult with computed scores
    """
    ...
```

### Async/Await

Use async/await for I/O operations:

```python
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Error Handling

- Use specific exception types
- Log errors with context
- Return meaningful error messages to API consumers

```python
from fastapi import HTTPException

async def get_startup(startup_id: UUID) -> Startup:
    startup = await db.get(startup_id)
    if not startup:
        raise HTTPException(
            status_code=404,
            detail=f"Startup {startup_id} not found"
        )
    return startup
```

### Database Queries

Use SQLAlchemy 2.0 style with async:

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

stmt = (
    select(Startup)
    .where(Startup.id == startup_id)
    .options(selectinload(Startup.scores))
)
result = await db.execute(stmt)
startup = result.scalar_one_or_none()
```

## Testing

### Test Structure

Place tests in the `tests/` directory mirroring the source structure:

```
tests/
├── test_api/
│   ├── test_startups.py
│   └── test_auth.py
├── test_bots/
│   ├── test_runway_bot.py
│   └── test_pmf_bot.py
└── conftest.py
```

### Writing Tests

Use pytest with async support:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_startup(client: AsyncClient):
    response = await client.post(
        "/startup",
        json={"name": "Test Startup", "domain": "test.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Startup"
```

### Fixtures

Use `conftest.py` for shared fixtures:

```python
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    from startupintel.api.main import create_app
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_client(client: AsyncClient, db):
    # Create and authenticate user
    await client.post("/api/auth/register", json={...})
    response = await client.post("/api/auth/login", json={...})
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api/test_startups.py

# Run with coverage
pytest --cov=startupintel --cov-report=html

# Run in parallel
pytest -n auto
```

## Submitting Changes

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure CI passes** (tests, linting, type checking)
4. **Fill out the PR template** with:
   - Description of changes
   - Related issue numbers
   - Testing performed
   - Screenshots (if UI changes)

5. **Request review** from maintainers
6. **Address feedback** promptly
7. **Squash commits** if requested

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No new security vulnerabilities introduced
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Version bumped (if applicable)

### Commit Messages

Write clear, descriptive commit messages:

```
Add email notification system for startup alerts

- Implement EmailNotifier class with SendGrid and SES support
- Add HTML email templates with action buttons
- Integrate with notification manager for batch operations
- Add configuration options for email providers
```

Format: `<type>: <subject>` where type is:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build process, dependencies, etc.

## Release Process

1. **Version Bumping**: Update version in `pyproject.toml`
2. **CHANGELOG**: Update `CHANGELOG.md` with new features and fixes
3. **Tagging**: Create annotated git tag: `git tag -a v1.2.3 -m "Release 1.2.3"`
4. **CI/CD**: Push tag to trigger release workflow
5. **Docker**: Ensure Docker image is built and pushed
6. **Docs**: Update documentation site if applicable

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Join our community chat (if available)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to StartupIntel!
