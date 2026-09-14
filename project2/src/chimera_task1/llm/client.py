"""Bounded localhost-only OpenAI-compatible LLM client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: Literal["system", "user"]
    content: str


@dataclass(frozen=True, slots=True)
class LlmGenerationConfig:
    model: str
    model_version: str
    temperature: float = 0.2
    top_p: float = 0.8
    max_tokens: int = 768
    seed: int = 20260812
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not 0 <= self.temperature <= 2 or not 0 < self.top_p <= 1:
            raise ValueError("invalid sampling configuration")
        if self.max_tokens <= 0 or self.timeout_seconds <= 0:
            raise ValueError("generation limits must be positive")


class LlmTimeoutError(RuntimeError):
    pass


class LlmProviderError(RuntimeError):
    pass


class LlmClient(Protocol):
    async def complete(
        self,
        messages: tuple[LlmMessage, ...],
        config: LlmGenerationConfig,
    ) -> str: ...


class LocalOpenAiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434/v1") -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("LLM base URL must be localhost HTTP")
        self._url = base_url.rstrip("/") + "/chat/completions"

    async def complete(
        self,
        messages: tuple[LlmMessage, ...],
        config: LlmGenerationConfig,
    ) -> str:
        payload = {
            "model": config.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "seed": config.seed,
        }
        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(self._url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("llm_timeout") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LlmProviderError("llm_provider_error") from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmProviderError("llm_response_shape_invalid") from exc
        if not isinstance(content, str) or not content.strip():
            raise LlmProviderError("llm_response_content_invalid")
        return content
