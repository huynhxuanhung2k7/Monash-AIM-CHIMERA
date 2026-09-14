"""Minimal async retrieval protocol used by the MCP adapter and tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from chimera_task1.contracts.retrieval import Task1RevealSection


class RetrievalClient(Protocol):
    async def retrieve(self, section: Task1RevealSection) -> str | None: ...


class InMemoryRetrievalClient:
    def __init__(self, values: Mapping[Task1RevealSection, str | None]) -> None:
        self._values = dict(values)
        self.calls: list[Task1RevealSection] = []

    async def retrieve(self, section: Task1RevealSection) -> str | None:
        self.calls.append(section)
        return self._values.get(section)
