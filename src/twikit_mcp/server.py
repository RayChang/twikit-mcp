"""Minimal server entrypoint scaffold for Task 1."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MCPStub:
    """Explicit placeholder contract for the future MCP server."""

    name: str = "twikit-mcp"


def build_mcp():
    """Build and return the MCP server placeholder."""
    return MCPStub()
