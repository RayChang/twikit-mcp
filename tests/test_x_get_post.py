import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def make_tweet(tweet_id="123"):
    return SimpleNamespace(
        id=tweet_id,
        text="hello",
        created_at=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        view_count=100,
        user=SimpleNamespace(name="Alice", screen_name="alice", verified=False),
        media=[],
        hashtags=[],
        urls=[],
        mentions=[],
    )


class FakePostClient:
    def __init__(self):
        self.calls = []

    async def get_tweet_by_id(self, tweet_id):
        self.calls.append(tweet_id)
        return make_tweet(tweet_id)


def test_x_get_post_accepts_twitter_url():
    from twikit_mcp.service import PostService

    client = FakePostClient()
    service = PostService(client=client)

    result = asyncio.run(service.get_post(url="https://twitter.com/user/status/123?ref=share"))

    assert client.calls == ["123"]
    assert result.id == "123"
    assert result.url == "https://x.com/alice/status/123"
    assert result.view_count == 100


def test_x_get_post_accepts_plain_id():
    from twikit_mcp.service import PostService

    client = FakePostClient()
    service = PostService(client=client)

    result = asyncio.run(service.get_post(id="456"))

    assert client.calls == ["456"]
    assert result.id == "456"


def test_x_get_post_requires_exactly_one_identifier():
    from twikit_mcp.query import QueryError
    from twikit_mcp.service import PostService

    service = PostService(client=FakePostClient())

    with pytest.raises(QueryError):
        asyncio.run(service.get_post())

    with pytest.raises(QueryError):
        asyncio.run(service.get_post(url="https://x.com/user/status/123", id="123"))


def test_build_mcp_registers_x_get_post_tool():
    from twikit_mcp.server import MCPStub, build_mcp
    from twikit_mcp.service import PostService

    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        post_service=PostService(client=FakePostClient()),
    )

    assert "x_get_post" in mcp.tools


def test_registered_x_get_post_tool_returns_json_dict():
    from twikit_mcp.server import MCPStub, build_mcp
    from twikit_mcp.service import PostService

    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        post_service=PostService(client=FakePostClient()),
    )

    result = asyncio.run(mcp.tools["x_get_post"](id="123"))

    assert result["id"] == "123"
    assert result["view_count"] == 100
