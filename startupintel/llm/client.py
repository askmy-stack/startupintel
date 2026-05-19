"""LLM client with unified interface for Groq and Ollama providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from startupintel.config import get_settings

if TYPE_CHECKING:
    from groq import AsyncGroq


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text from a prompt."""

    @abstractmethod
    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **kwargs: dict,
    ) -> str:
        """Generate a diagnosis for a bot result."""


class GroqClient(BaseLLMClient):
    """Groq API client for fast inference."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or get_settings().groq_api_key
        self.model = model or get_settings().groq_model
        self.timeout = get_settings().llm_timeout
        self._client: AsyncGroq | None = None

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            from groq import AsyncGroq

            if not self.api_key:
                raise ValueError("Groq API key not configured")
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a startup intelligence analyst."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error generating response: {e}"

    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **kwargs: dict,
    ) -> str:
        formatted_prompt = prompt_template.format(
            bot_name=bot_name,
            score=score,
            signal_breakdown=signal_breakdown,
            similar_cases=similar_cases,
            **kwargs,
        )
        return await self.generate(formatted_prompt, max_tokens=400)


class OllamaClient(BaseLLMClient):
    """Ollama client for local inference."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or get_settings().ollama_base_url).rstrip("/")
        self.model = model or get_settings().ollama_model
        self.timeout = get_settings().llm_timeout

    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": max_tokens, "temperature": 0.3},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            return f"Error generating response from Ollama: {e}"

    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **kwargs: dict,
    ) -> str:
        formatted_prompt = prompt_template.format(
            bot_name=bot_name,
            score=score,
            signal_breakdown=signal_breakdown,
            similar_cases=similar_cases,
            **kwargs,
        )
        return await self.generate(formatted_prompt, max_tokens=400)


class LLMClient(BaseLLMClient):
    """Unified LLM client that switches between providers based on config."""

    def __init__(self, provider: str | None = None):
        self.provider = provider or get_settings().llm_provider
        self._client: BaseLLMClient | None = None

    @property
    def client(self) -> BaseLLMClient:
        if self._client is None:
            if self.provider == "groq":
                self._client = GroqClient()
            elif self.provider == "ollama":
                self._client = OllamaClient()
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        return await self.client.generate(prompt, max_tokens)

    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **kwargs: dict,
    ) -> str:
        return await self.client.generate_diagnosis(
            bot_name, score, signal_breakdown, similar_cases, prompt_template, **kwargs
        )


class NullLLMClient(BaseLLMClient):
    """Fallback client that returns placeholder responses."""

    async def generate(self, prompt: str, max_tokens: int = 500) -> str:
        return f"[NullLLM] Prompt: {prompt[:100]}..."

    async def generate_diagnosis(
        self,
        bot_name: str,
        score: float,
        signal_breakdown: dict,
        similar_cases: list[dict],
        prompt_template: str,
        **kwargs: dict,
    ) -> str:
        return (
            f"{bot_name} score is {score}/100 based on {signal_breakdown}. "
            f"Similar case count: {len(similar_cases)}."
        )


def get_llm_client() -> BaseLLMClient:
    """Factory function to get the appropriate LLM client."""
    settings = get_settings()
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return LLMClient("groq")
    elif settings.llm_provider == "ollama":
        return LLMClient("ollama")
    return NullLLMClient()

