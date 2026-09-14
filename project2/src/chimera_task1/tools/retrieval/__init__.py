"""Patient-section retrieval client surfaces."""

from .client import InMemoryRetrievalClient, RetrievalClient
from .mcp_client import McpRetrievalClient, McpRetrievalError

__all__ = [
    "InMemoryRetrievalClient",
    "McpRetrievalClient",
    "McpRetrievalError",
    "RetrievalClient",
]
