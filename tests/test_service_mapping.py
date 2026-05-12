from datetime import UTC, datetime
from types import SimpleNamespace


def make_tweet(**overrides):
    values = {
        "id": "1",
        "text": "hello",
        "created_at": datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
        "lang": "en",
        "favorite_count": 1,
        "retweet_count": 2,
        "reply_count": 3,
        "quote_count": 4,
        "user": SimpleNamespace(name="Alice", screen_name="alice", verified=False),
        "media": [],
        "hashtags": [],
        "urls": [],
        "mentions": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_map_tweet_to_search_summary():
    from tweety_mcp.service import map_tweet_to_search_summary

    result = map_tweet_to_search_summary(make_tweet())

    assert result.id == "1"
    assert result.url == "https://x.com/alice/status/1"
    assert result.text == "hello"
    assert result.created_at == "2026-05-11T00:00:00Z"
    assert result.author.handle == "alice"


def test_map_tweet_to_search_summary_detects_shape_flags():
    from tweety_mcp.service import map_tweet_to_search_summary

    result = map_tweet_to_search_summary(
        make_tweet(
            in_reply_to_status_id="9",
            quote=make_tweet(id="2"),
            retweeted_tweet=make_tweet(id="3"),
            media=[SimpleNamespace(type="photo", url="https://cdn.example/photo.jpg")],
        )
    )

    assert result.has_media is True
    assert result.is_reply is True
    assert result.is_quote is True
    assert result.is_retweet is True


def test_map_tweet_to_search_summary_requires_author_handle():
    import pytest

    from tweety_mcp.service import map_tweet_to_search_summary

    with pytest.raises(ValueError):
        map_tweet_to_search_summary(make_tweet(user=SimpleNamespace(name="Alice")))


def test_map_tweet_to_full_post_includes_entities_and_nested_posts():
    from tweety_mcp.service import map_tweet_to_full_post

    result = map_tweet_to_full_post(
        make_tweet(
            view_count=100,
            hashtags=["ai"],
            urls=["https://example.com"],
            mentions=["bob"],
            media=[SimpleNamespace(type="photo", url="https://cdn.example/photo.jpg", alt_text="chart")],
            in_reply_to_status_id="9",
            in_reply_to_user=SimpleNamespace(screen_name="bob"),
            quote=make_tweet(id="2", user=SimpleNamespace(name="Bob", screen_name="bob", verified=True)),
        )
    )

    assert result.view_count == 100
    assert result.hashtags == ["ai"]
    assert result.urls == ["https://example.com"]
    assert result.mentions == ["bob"]
    assert result.media[0].alt_text == "chart"
    assert result.in_reply_to_status_id == "9"
    assert result.in_reply_to_user_handle == "bob"
    assert result.quoted_post is not None
    assert result.quoted_post.id == "2"
