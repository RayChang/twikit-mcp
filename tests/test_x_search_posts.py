from datetime import UTC, datetime
import asyncio
from types import SimpleNamespace

import pytest


def make_tweet(tweet_id="1", text="hello"):
    return SimpleNamespace(
        id=tweet_id,
        text=text,
        created_at=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        user=SimpleNamespace(name="Alice", screen_name="alice", verified=False),
        media=[],
        hashtags=[],
        urls=[],
        mentions=[],
    )


class FakeResult(list):
    def __init__(self, items, *, next_cursor=None, next_result=None):
        super().__init__(items)
        self.next_cursor = next_cursor
        self.cursor = next_cursor
        self._next_result = next_result

    async def next(self):
        return self._next_result


class FakeSearchClient:
    def __init__(self):
        self.calls = []
        self.result = FakeResult([make_tweet()], next_cursor="cursor-1")

    async def search_tweet(self, query, mode):
        self.calls.append((query, mode))
        return self.result


class FakeActivatingSearchClient(FakeSearchClient):
    def __init__(self):
        super().__init__()
        self.activate_calls = 0

    async def activate(self):
        self.activate_calls += 1


def test_x_search_posts_returns_summary_listing():
    from twikit_mcp.service import SearchService

    client = FakeSearchClient()
    service = SearchService(client=client)

    result = asyncio.run(service.search_posts(query="AI", author="@alice", limit=20))

    assert client.calls == [("AI from:alice", "Latest")]
    assert result.items[0].id == "1"
    assert result.next_cursor == "cursor-1"


def test_x_search_posts_activates_guest_client_once():
    from twikit_mcp.service import SearchService

    client = FakeActivatingSearchClient()
    service = SearchService(client=client)

    asyncio.run(service.search_posts(query="AI"))
    asyncio.run(service.search_posts(query="AI"))

    assert client.activate_calls == 1


def test_x_search_posts_uses_cursor_to_fetch_next_page():
    from twikit_mcp.service import SearchService

    first = FakeResult(
        [make_tweet("1")],
        next_cursor="cursor-1",
        next_result=FakeResult([make_tweet("2")], next_cursor="cursor-2"),
    )
    client = FakeSearchClient()
    client.result = first
    service = SearchService(client=client)

    asyncio.run(service.search_posts(query="AI"))
    result = asyncio.run(service.search_posts(query="AI", cursor="cursor-1"))

    assert result.items[0].id == "2"
    assert result.next_cursor == "cursor-2"


def test_x_search_posts_rejects_limit_above_max():
    from twikit_mcp.service import SearchService
    from twikit_mcp.query import QueryError

    service = SearchService(client=FakeSearchClient())

    with pytest.raises(QueryError):
        asyncio.run(service.search_posts(query="AI", limit=51))


def test_x_search_posts_rejects_unknown_cursor():
    from twikit_mcp.service import SearchService
    from twikit_mcp.query import QueryError

    service = SearchService(client=FakeSearchClient())

    with pytest.raises(QueryError):
        asyncio.run(service.search_posts(query="AI", cursor="missing"))


def test_build_mcp_registers_x_search_posts_tool():
    from twikit_mcp.server import MCPStub, build_mcp
    from twikit_mcp.service import SearchService

    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        search_service=SearchService(client=FakeSearchClient()),
    )

    assert "x_search_posts" in mcp.tools


def test_registered_x_search_posts_tool_returns_json_dict():
    from twikit_mcp.server import MCPStub, build_mcp
    from twikit_mcp.service import SearchService

    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        search_service=SearchService(client=FakeSearchClient()),
    )

    result = asyncio.run(mcp.tools["x_search_posts"](query="AI"))

    assert result["items"][0]["id"] == "1"
    assert result["next_cursor"] == "cursor-1"
