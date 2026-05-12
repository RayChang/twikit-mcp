"""MCP server construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from twikit_mcp.client_factory import TwikitClientFactory
from twikit_mcp.config import load_runtime_config
from twikit_mcp.service import BookmarkService, PostService, SearchService


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


def build_mcp(*, mcp_factory=None, search_service=None, post_service=None, bookmark_service=None):
    """Build and return the MCP server."""
    factory = mcp_factory or _default_mcp_factory
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

    if bookmark_service is not None:

        @mcp.tool()
        async def x_get_bookmarks(
            query: str | None = None,
            author: str | None = None,
            since: str | None = None,
            until: str | None = None,
            lang: str | None = None,
            limit: int = 20,
            cursor: str | None = None,
        ):
            result = await bookmark_service.get_bookmarks(
                query=query,
                author=author,
                since=since,
                until=until,
                lang=lang,
                limit=limit,
                cursor=cursor,
            )
            return result.model_dump()

    return mcp


def main() -> None:
    """Console script entrypoint for stdio MCP hosts."""
    config = load_runtime_config()
    client = TwikitClientFactory().create_client(config)
    mcp = build_mcp(
        search_service=SearchService(client=client),
        post_service=PostService(client=client),
        bookmark_service=BookmarkService(client=client, authenticated=config.mode == "cookie-auth"),
    )
    mcp.run()


def _default_mcp_factory(name: str):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("mcp Python SDK is required to run twikit-mcp") from exc
    return FastMCP(name)
