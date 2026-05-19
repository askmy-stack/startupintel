"""Tests for LLM client."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from startupintel.llm.client import BaseLLMClient, GroqClient, OllamaClient, get_llm_client


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        return f"Mock response: {prompt[:20]}..."

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


@pytest.mark.asyncio
async def test_base_llm_client():
    """Test base LLM client."""
    client = MockLLMClient()

    response = await client.complete("Test prompt")
    assert "Mock response" in response

    embeddings = await client.embed(["text1", "text2"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384


def test_get_llm_client_groq():
    """Test getting Groq client."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(
            llm_provider="groq",
            groq_api_key="test-key",
            groq_model="llama-3.3-70b-versatile",
            llm_timeout=60.0,
        )

        with patch.object(GroqClient, "__init__", return_value=None):
            client = get_llm_client()
            assert isinstance(client, GroqClient)


def test_get_llm_client_ollama():
    """Test getting Ollama client."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(
            llm_provider="ollama",
            ollama_base_url="http://localhost:11434",
            ollama_model="gemma3:4b",
            llm_timeout=60.0,
        )

        with patch.object(OllamaClient, "__init__", return_value=None):
            client = get_llm_client()
            assert isinstance(client, OllamaClient)
