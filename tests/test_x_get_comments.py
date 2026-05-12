import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def make_tweet(tweet_id, *, text="reply", handle="bob"):
    return SimpleNamespace(
        id=tweet_id,
        text=text,
        created_at=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
        lang="en",
        favorite_count=0,
        retweet_count=0,
        reply_count=0,
        quote_count=0,
        user=SimpleNamespace(name="Bob", screen_name=handle, verified=False),
        media=[],
        hashtags=[],
        urls=[],
        mentions=[],
    )


class FakeCommentsResult:
    """Simulates a tweety _CommentsPage: iterable of top-level tweets + cursor."""

    def __init__(self, tweets, next_cursor=None):
        self._tweets = tweets
        self.next_cursor = next_cursor

    def __iter__(self):
        return iter(self._tweets)


class FakeCommentClient:
    def __init__(self, result):
        self._result = result
        self.calls = []

    async def get_tweet_comments(self, post_id, count=20, cursor=None):
        self.calls.append((post_id, count, cursor))
        return self._result


def test_comment_service_returns_top_level_replies():
    from tweety_mcp.service import CommentService

    tweets = [
        make_tweet("11", text="first reply", handle="alice"),
        make_tweet("22", text="second reply", handle="carol"),
    ]
    service = CommentService(
        client=FakeCommentClient(FakeCommentsResult(tweets, next_cursor="CUR1"))
    )
    result = asyncio.run(service.get_comments(id="999"))

    assert len(result.items) == 2
    assert result.items[0].id == "11"
    assert result.items[0].text == "first reply"
    assert result.items[0].author.handle == "alice"
    assert result.items[1].id == "22"
    assert result.next_cursor == "CUR1"


def test_comment_service_respects_limit():
    from tweety_mcp.service import CommentService

    tweets = [make_tweet(str(i)) for i in range(5)]
    service = CommentService(client=FakeCommentClient(FakeCommentsResult(tweets)))
    result = asyncio.run(service.get_comments(id="999", limit=3))

    assert len(result.items) == 3


def test_comment_service_requires_one_of_url_or_id():
    from tweety_mcp.query import QueryError
    from tweety_mcp.service import CommentService

    service = CommentService(client=FakeCommentClient(FakeCommentsResult([])))
    with pytest.raises(QueryError):
        asyncio.run(service.get_comments())
    with pytest.raises(QueryError):
        asyncio.run(service.get_comments(id="123", url="https://x.com/a/status/123"))


def test_comment_service_rejects_invalid_limit():
    from tweety_mcp.query import QueryError
    from tweety_mcp.service import CommentService

    service = CommentService(client=FakeCommentClient(FakeCommentsResult([])))
    with pytest.raises(QueryError):
        asyncio.run(service.get_comments(id="999", limit=0))
    with pytest.raises(QueryError):
        asyncio.run(service.get_comments(id="999", limit=999))


def test_x_get_comments_tool_returns_dict():
    from tweety_mcp.server import MCPStub, build_mcp
    from tweety_mcp.service import CommentService

    service = CommentService(
        client=FakeCommentClient(FakeCommentsResult([make_tweet("11")]))
    )
    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        comment_service=service,
    )

    result = asyncio.run(mcp.tools["x_get_comments"](id="999"))
    assert isinstance(result, dict)
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == "11"
