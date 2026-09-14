"""Scripted deterministic LLM for unit and integration tests."""

from __future__ import annotations

from chimera_task1.llm.client import LlmGenerationConfig, LlmMessage


class ScriptedLlmClient:
    def __init__(self, responses: list[str | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[tuple[LlmMessage, ...], LlmGenerationConfig]] = []

    async def complete(
        self,
        messages: tuple[LlmMessage, ...],
        config: LlmGenerationConfig,
    ) -> str:
        self.calls.append((messages, config))
        if not self._responses:
            raise RuntimeError("no_scripted_response")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
