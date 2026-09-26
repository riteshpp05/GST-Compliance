"""
app.agent.ai.provider
=====================
LLM Provider Abstraction for UC15 (Sprint 12.1).
Decouples application code from specific LLM SDKs or vendor implementations.
Handles configuration from environment variables, safe fallback when API keys are missing,
and mock provider injection for test stability.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderUnavailableError(Exception):
    """Raised when an operation requires an LLM provider but none is available."""
    pass


class LLMConfig(BaseModel):
    """Typed configuration for LLM Provider."""
    provider_name: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").lower())
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.0")))
    timeout: float = Field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "30.0")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2000")))
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or getattr(settings, "llm_api_key", None)
    )


class LLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self.config = config or LLMConfig()

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is configured with valid credentials."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate unstructured text response from prompt."""
        pass

    @abstractmethod
    def structured_generate(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate structured Pydantic response adhering to specified schema."""
        pass


class DisabledProvider(LLMProvider):
    """Fallback provider used when no API key is configured or AI is disabled."""

    def is_available(self) -> bool:
        return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        raise LLMProviderUnavailableError("AI Provider is unavailable. No API key configured.")

    def structured_generate(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        raise LLMProviderUnavailableError("AI Provider is unavailable. No API key configured.")


class MockProvider(LLMProvider):
    """Controlled mock provider for unit tests and offline testing."""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        mock_response: Optional[str] = None,
        mock_structured: Optional[Dict[str, Any]] = None,
        available: bool = True,
    ) -> None:
        super().__init__(config)
        env = os.getenv("APP_ENV", "development").lower().strip()
        if env in ("production", "prod"):
            raise ValueError(
                "Security violation: MockProvider cannot be instantiated in PRODUCTION environment (APP_ENV=production)."
            )
        self._available = available
        self.mock_response = mock_response or "Mock LLM synthesized response."
        self.mock_structured = mock_structured or {}

    def is_available(self) -> bool:
        return self._available

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self._available:
            raise LLMProviderUnavailableError("Mock LLM Provider set to unavailable.")
        return self.mock_response

    def structured_generate(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self._available:
            raise LLMProviderUnavailableError("Mock LLM Provider set to unavailable.")
        if self.mock_structured:
            return schema.model_validate(self.mock_structured)
        # Attempt to parse mock_response if JSON
        try:
            data = json.loads(self.mock_response)
            return schema.model_validate(data)
        except Exception:
            # Construct minimal valid object if schema requires fields
            dummy_data = {}
            for name, field in schema.model_fields.items():
                if field.annotation is str:
                    dummy_data[name] = "Mock value"
                elif field.annotation is list or getattr(field.annotation, "__origin__", None) is list:
                    dummy_data[name] = []
                elif field.annotation is dict or getattr(field.annotation, "__origin__", None) is dict:
                    dummy_data[name] = {}
                else:
                    dummy_data[name] = None
            return schema.model_validate(dummy_data)


class OpenAIProvider(LLMProvider):
    """
    Standard OpenAI API Provider implementation using HTTP client (httpx).
    Safely degrades to unavailable if API key is missing.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        super().__init__(config)
        self.api_key = self.config.api_key

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise LLMProviderUnavailableError("OpenAI API key missing.")
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    def structured_generate(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.is_available():
            raise LLMProviderUnavailableError("OpenAI API key missing.")
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        sys_instructions = (system_prompt or "") + "\nYou MUST respond strictly in valid JSON matching the requested schema."
        messages.append({"role": "system", "content": sys_instructions.strip()})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return schema.model_validate(parsed)
        except Exception as e:
            logger.error(f"OpenAI structured API call failed: {e}")
            raise RuntimeError(f"OpenAI structured API call failed: {e}") from e


def create_llm_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """Factory function creating the appropriate LLM provider based on config and env."""
    cfg = config or LLMConfig()
    env = os.getenv("APP_ENV", "development").lower().strip()

    if cfg.provider_name == "mock":
        if env in ("production", "prod"):
            logger.error("Security violation: Mock LLM provider requested in PRODUCTION environment. Returning DisabledProvider.")
            return DisabledProvider(config=cfg)
        return MockProvider(config=cfg)

    if cfg.api_key and cfg.api_key.strip():
        return OpenAIProvider(config=cfg)

    return DisabledProvider(config=cfg)
