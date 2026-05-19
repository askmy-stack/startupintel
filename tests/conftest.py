"""Pytest configuration and fixtures for StartupIntel tests."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4

from startupintel.db.models import Startup, Investor, Accelerator, StartupScore


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def sample_startup():
    """Create a sample startup for testing."""
    return Startup(
        id=uuid4(),
        name="Test Startup",
        domain="teststartup.io",
        founded_year=2022,
        industry="saas",
        stage="seed",
        employee_count=25,
        total_funding_usd=2_500_000,
        last_funding_date=datetime.utcnow(),
    )


@pytest.fixture
def sample_investor():
    """Create a sample investor for testing."""
    return Investor(
        id=uuid4(),
        name="Test Investor",
        firm="Test Capital",
        centrality_score=0.85,
        value_add_score=0.78,
        portfolio_count=42,
    )


@pytest.fixture
def sample_accelerator():
    """Create a sample accelerator for testing."""
    return Accelerator(
        id=uuid4(),
        name="Test Accelerator",
        location="San Francisco, CA",
        cohort_count=50,
        follow_on_rate=0.70,
        roi_score=85.0,
    )


@pytest.fixture
def sample_score(sample_startup):
    """Create a sample startup score for testing."""
    return StartupScore(
        id=uuid4(),
        startup_id=sample_startup.id,
        bot_name="runway",
        score=65.0,
        signal_breakdown={"headcount": 0.7, "job_postings": 0.6},
        llm_diagnosis="Test diagnosis",
    )
