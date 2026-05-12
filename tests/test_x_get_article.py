import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def make_article_tweet(*, has_article=True):
    article = SimpleNamespace(
        id="article-99",
        title="Article Title",
        preview_text="Preview",
        text="Body text",
        cover_media=SimpleNamespace(direct_url="https://cdn.example/cover.jpg", alt_text="cover"),
        media=[
            SimpleNamespace(direct_url="https://cdn.example/img1.jpg", alt_text="img1"),
        ],
    )
    return SimpleNamespace(
        id="parent-tweet",
        article=article if has_article else None,
        author=SimpleNamespace(name="Alice", screen_name="alice", verified=True),
        created_at=datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
    )


class FakeArticleClient:
    def __init__(self, tweet):
        self._tweet = tweet
        self.calls = []

    async def get_tweet_by_id(self, tweet_id):
        self.calls.append(tweet_id)
        return self._tweet


def test_article_service_returns_payload_when_article_present():
    from tweety_mcp.service import ArticleService

    service = ArticleService(client=FakeArticleClient(make_article_tweet()))
    result = asyncio.run(service.get_article(id="2052796100608974848"))

    assert result.id == "article-99"
    assert result.title == "Article Title"
    assert result.text == "Body text"
    assert result.url == "https://x.com/i/article/article-99"
    assert result.author.handle == "alice"
    assert result.cover_media is not None
    assert result.cover_media.url == "https://cdn.example/cover.jpg"
    assert len(result.media) == 1
    assert result.media[0].url == "https://cdn.example/img1.jpg"


def test_article_service_rejects_post_without_article():
    from tweety_mcp.query import QueryError
    from tweety_mcp.service import ArticleService

    service = ArticleService(client=FakeArticleClient(make_article_tweet(has_article=False)))
    with pytest.raises(QueryError):
        asyncio.run(service.get_article(id="2052796100608974848"))


def test_article_service_rejects_missing_inputs():
    from tweety_mcp.query import QueryError
    from tweety_mcp.service import ArticleService

    service = ArticleService(client=FakeArticleClient(make_article_tweet()))
    with pytest.raises(QueryError):
        asyncio.run(service.get_article())
