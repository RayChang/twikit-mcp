import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def make_tweet(tweet_id="1", text="AI note", *, author="alice", created_at=None, lang="en"):
    return SimpleNamespace(
        id=tweet_id,
        text=text,
        created_at=created_at or datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
        lang=lang,
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        user=SimpleNamespace(name=author.title(), screen_name=author, verified=False),
        media=[],
        hashtags=[],
        urls=[],
        mentions=[],
    )


class FakeBookmarkResult(list):
    def __init__(self, items, *, next_cursor=None, next_result=None):
        super().__init__(items)
        self.next_cursor = next_cursor
        self.cursor = next_cursor
        self._next_result = next_result

    async def next(self):
        return self._next_result


class FakeBookmarkClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def get_bookmarks(self, count=20):
        self.calls.append(count)
        return self.result


def test_x_get_bookmarks_requires_auth():
    from twikit_mcp.errors import AuthRequiredError
    from twikit_mcp.service import BookmarkService

    service = BookmarkService(client=FakeBookmarkClient(FakeBookmarkResult([])), authenticated=False)

    with pytest.raises(AuthRequiredError):
        asyncio.run(service.get_bookmarks(limit=20))


def test_x_get_bookmarks_returns_listing_for_authenticated_client():
    from twikit_mcp.service import BookmarkService

    client = FakeBookmarkClient(FakeBookmarkResult([make_tweet()], next_cursor="cursor-1"))
    service = BookmarkService(client=client, authenticated=True)

    result = asyncio.run(service.get_bookmarks(limit=20))

    assert client.calls == [20]
    assert result.items[0].id == "1"
    assert result.next_cursor == "cursor-1"
    assert result.partial is False
    assert result.scanned_pages == 1


def test_x_get_bookmarks_filters_by_query_author_time_and_lang():
    from twikit_mcp.service import BookmarkService

    result = FakeBookmarkResult(
        [
            make_tweet("1", "Taylor Swift tour", author="alice", lang="en"),
            make_tweet("2", "AI note", author="bob", lang="en"),
            make_tweet(
                "3",
                "Taylor Swift old",
                author="alice",
                created_at=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
                lang="en",
            ),
            make_tweet("4", "Taylor Swift tour", author="alice", lang="ja"),
        ]
    )
    service = BookmarkService(client=FakeBookmarkClient(result), authenticated=True)

    response = asyncio.run(
        service.get_bookmarks(
            query="Taylor",
            author="@alice",
            since="2026-05-01",
            until="2026-05-31",
            lang="en",
            limit=20,
        )
    )

    assert [item.id for item in response.items] == ["1"]


def test_x_get_bookmarks_scans_multiple_pages_for_filtered_results():
    from twikit_mcp.service import BookmarkService

    second = FakeBookmarkResult([make_tweet("2", "target")], next_cursor="cursor-2")
    first = FakeBookmarkResult([make_tweet("1", "other")], next_cursor="cursor-1", next_result=second)
    service = BookmarkService(client=FakeBookmarkClient(first), authenticated=True)

    response = asyncio.run(service.get_bookmarks(query="target", limit=1))

    assert [item.id for item in response.items] == ["2"]
    assert response.scanned_pages == 2


def test_x_get_bookmarks_uses_cursor_to_fetch_next_page():
    from twikit_mcp.service import BookmarkService

    second = FakeBookmarkResult([make_tweet("2")], next_cursor="cursor-2")
    first = FakeBookmarkResult([make_tweet("1")], next_cursor="cursor-1", next_result=second)
    service = BookmarkService(client=FakeBookmarkClient(first), authenticated=True)

    asyncio.run(service.get_bookmarks(limit=20))
    response = asyncio.run(service.get_bookmarks(cursor="cursor-1", limit=20))

    assert [item.id for item in response.items] == ["2"]
    assert response.next_cursor == "cursor-2"


def test_build_mcp_registers_x_get_bookmarks_tool():
    from twikit_mcp.server import MCPStub, build_mcp
    from twikit_mcp.service import BookmarkService

    mcp = build_mcp(
        mcp_factory=lambda name: MCPStub(name=name),
        bookmark_service=BookmarkService(client=FakeBookmarkClient(FakeBookmarkResult([])), authenticated=True),
    )

    assert "x_get_bookmarks" in mcp.tools
