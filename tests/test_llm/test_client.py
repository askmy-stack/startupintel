"""Tests for the unified LLM client."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from startupintel.llm.client import (
    BaseLLMClient,
    GroqClient,
    LLMClient,
    NullLLMClient,
    OllamaClient,
    get_llm_client,
)


def test_base_is_abstract():
    """BaseLLMClient cannot be instantiated without implementing the interface."""
    with pytest.raises(TypeError):
        BaseLLMClient()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_null_client_generates_placeholder():
    """NullLLMClient returns deterministic placeholder text."""
    client = NullLLMClient()
    out = await client.generate("hello world")
    assert "[NullLLM]" in out

    diagnosis = await client.generate_diagnosis(
        bot_name="runway",
        score=42.0,
        signal_breakdown={"headcount": 0.5},
        similar_cases=[{"id": 1}, {"id": 2}],
        prompt_template="ignored",
    )
    assert "runway" in diagnosis
    assert "42" in diagnosis
    assert "2" in diagnosis  # similar case count


def test_get_llm_client_groq():
    """Groq provider with a key yields a Groq-backed unified client."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(llm_provider="groq", groq_api_key="k")
        client = get_llm_client()
        assert isinstance(client, LLMClient)
        assert client.provider == "groq"


def test_get_llm_client_ollama():
    """Ollama provider yields a unified client regardless of key."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(llm_provider="ollama", groq_api_key=None)
        client = get_llm_client()
        assert isinstance(client, LLMClient)
        assert client.provider == "ollama"


def test_get_llm_client_falls_back_to_null():
    """Groq selected but no key configured falls back to NullLLMClient."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(llm_provider="groq", groq_api_key=None)
        client = get_llm_client()
        assert isinstance(client, NullLLMClient)


def test_unified_client_selects_provider_class():
    """LLMClient.client lazily builds the provider-specific client."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(
            llm_provider="groq",
            groq_api_key="k",
            groq_model="m",
            llm_timeout=1.0,
            ollama_base_url="http://localhost:11434",
            ollama_model="g",
        )
        assert isinstance(LLMClient("groq").client, GroqClient)
        assert isinstance(LLMClient("ollama").client, OllamaClient)
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            _ = LLMClient("bogus").client


@pytest.mark.asyncio
async def test_groq_generate_wraps_errors():
    """GroqClient.generate returns a friendly message instead of raising."""
    with patch("startupintel.llm.client.get_settings") as mock_settings:
        mock_settings.return_value = Mock(
            groq_api_key=None, groq_model="m", llm_timeout=1.0
        )
        client = GroqClient()
        # No API key -> accessing .client raises inside generate, caught and wrapped.
        out = await client.generate("prompt")
        assert out.startswith("Error")
