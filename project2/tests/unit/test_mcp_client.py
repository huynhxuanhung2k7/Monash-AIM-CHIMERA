from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from chimera_task1.contracts.retrieval import Task1RevealSection
from chimera_task1.tools.retrieval import McpRetrievalClient, McpRetrievalError


@dataclass
class Text:
    text: str


@dataclass
class Result:
    content: tuple[Text, ...]
    isError: bool = False


class Session:
    def __init__(self, result: Result) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    async def call_tool(
        self, name: str, arguments: dict[str, object] | None = None
    ) -> Result:
        self.calls.append((name, arguments))
        return self.result


def test_mcp_adapter_uses_closed_no_argument_tool_mapping() -> None:
    session = Session(Result((Text("MRI report text"),)))
    client = McpRetrievalClient(session)
    content = asyncio.run(client.retrieve(Task1RevealSection.RADIOLOGY_REPORT))
    assert content == "MRI report text"
    assert session.calls == [("get_mri_report", {})]


def test_mcp_adapter_converts_tool_error_to_safe_failure() -> None:
    client = McpRetrievalClient(Session(Result((), isError=True)))
    with pytest.raises(McpRetrievalError, match="mcp_tool_error"):
        asyncio.run(client.retrieve(Task1RevealSection.PSA_TREND))
