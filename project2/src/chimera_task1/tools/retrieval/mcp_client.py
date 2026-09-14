"""MCP stdio-session adapter for the five approved no-argument tools."""

from __future__ import annotations

from typing import Any, Protocol

from chimera_task1.contracts.retrieval import TOOL_BY_SECTION, Task1RevealSection


class McpSession(Protocol):
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object] | None = None,
    ) -> Any: ...


class McpRetrievalError(RuntimeError):
    pass


class McpRetrievalClient:
    """Call only the closed retrieval registry and return text content."""

    def __init__(self, session: McpSession) -> None:
        self._session = session
        self.calls: list[Task1RevealSection] = []

    async def retrieve(self, section: Task1RevealSection) -> str | None:
        self.calls.append(section)
        result = await self._session.call_tool(
            TOOL_BY_SECTION[section].value,
            arguments={},
        )
        if bool(getattr(result, "isError", False)):
            raise McpRetrievalError("mcp_tool_error")
        text_parts: list[str] = []
        for item in getattr(result, "content", ()):
            text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
        return "\n".join(text_parts) or None
