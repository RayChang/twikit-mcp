"""MCP server construction."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class MCPStub:
    """Small in-process stand-in used until the real SDK is wired in."""

    name: str = "twikit-mcp"
    tools: dict[str, Callable[..., Any]] | None = None

    def __post_init__(self) -> None:
        if self.tools is None:
            self.tools = {}

    def tool(self, name: str | None = None):
        def decorator(func):
            assert self.tools is not None
            self.tools[name or func.__name__] = func
            return func

        return decorator


def build_mcp(*, mcp_factory=None, search_service=None, post_service=None):
    """Build and return the MCP server."""
    factory = mcp_factory or MCPStub
    mcp = factory("twikit-mcp")

    if search_service is not None:

        @mcp.tool()
        async def x_search_posts(
            query: str,
            author: str | None = None,
            sort: str | None = None,
            since: str | None = None,
            until: str | None = None,
            lang: str | None = None,
            limit: int = 20,
            cursor: str | None = None,
        ):
            result = await search_service.search_posts(
                query=query,
                author=author,
                sort=sort,
                since=since,
                until=until,
                lang=lang,
                limit=limit,
                cursor=cursor,
            )
            return result.model_dump()

    if post_service is not None:

        @mcp.tool()
        async def x_get_post(url: str | None = None, id: str | None = None):
            result = await post_service.get_post(url=url, id=id)
            return result.model_dump()

    return mcp
