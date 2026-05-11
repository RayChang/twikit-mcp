from datetime import UTC, datetime
import tomllib


def test_search_post_summary_uses_iso_utc_timestamp():
    from twikit_mcp.models import SearchPostSummary

    item = SearchPostSummary(
        id="1",
        url="https://x.com/a/status/1",
        text="hello",
        created_at="2026-05-11T00:00:00Z",
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        has_media=False,
        is_reply=False,
        is_quote=False,
        is_retweet=False,
        author={"name": "A", "handle": "a", "verified": False},
    )

    assert item.created_at.endswith("Z")


def test_pyproject_declares_pydantic_runtime_dependency():
    with open("pyproject.toml", "rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.startswith("pydantic") for dependency in dependencies)


def test_search_post_summary_normalizes_offset_to_utc():
    from twikit_mcp.models import SearchPostSummary

    item = SearchPostSummary(
        id="1",
        url="https://x.com/a/status/1",
        text="hello",
        created_at="2026-05-11T08:00:00+08:00",
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        has_media=False,
        is_reply=False,
        is_quote=False,
        is_retweet=False,
        author={"name": "A", "handle": "a", "verified": False},
    )

    assert item.created_at == "2026-05-11T00:00:00Z"


def test_bookmark_list_response_accepts_bookmark_items():
    from twikit_mcp.models import BookmarkListResponse

    response = BookmarkListResponse(
        items=[
            {
                "id": "1",
                "url": "https://x.com/a/status/1",
                "text": "saved",
                "created_at": datetime(2026, 5, 11, 0, 0, tzinfo=UTC),
                "lang": "en",
                "favorite_count": 0,
                "retweet_count": 0,
                "reply_count": 0,
                "quote_count": 0,
                "has_media": False,
                "is_reply": False,
                "is_quote": False,
                "is_retweet": False,
                "author": {"name": "A", "handle": "a", "verified": False},
            }
        ],
        next_cursor="cursor-1",
        partial=True,
    )

    assert response.items[0].created_at == "2026-05-11T00:00:00Z"
    assert response.next_cursor == "cursor-1"
    assert response.partial is True


def test_rate_limited_error_sets_stable_code_and_retryable_flag():
    from twikit_mcp.errors import ErrorCode, rate_limited_error

    error = rate_limited_error(details={"reset_at": "2026-05-11T00:15:00Z"})

    assert error.code == ErrorCode.RATE_LIMITED
    assert error.retryable is True
    assert error.details == {"reset_at": "2026-05-11T00:15:00Z"}


def test_error_code_enum_covers_required_codes():
    from twikit_mcp.errors import ErrorCode

    assert {code.value for code in ErrorCode} == {
        "AUTH_REQUIRED",
        "AUTH_EXPIRED",
        "INVALID_POST_URL",
        "INVALID_ARGUMENT",
        "RATE_LIMITED",
        "NOT_FOUND",
        "UPSTREAM_CHANGED",
        "PARTIAL_RESULTS",
        "INTERNAL_ERROR",
    }


def test_full_post_payload_accepts_media_and_quoted_post():
    from twikit_mcp.models import FullPostPayload

    item = FullPostPayload(
        id="1",
        url="https://x.com/a/status/1",
        text="hello",
        created_at="2026-05-11T00:00:00Z",
        lang="en",
        favorite_count=1,
        retweet_count=2,
        reply_count=3,
        quote_count=4,
        has_media=True,
        is_reply=False,
        is_quote=True,
        is_retweet=False,
        author={"name": "A", "handle": "a", "verified": False},
        media=[{"type": "photo", "url": "https://cdn.example/photo.jpg", "alt_text": "chart"}],
        hashtags=["ai"],
        quoted_post={
            "id": "2",
            "url": "https://x.com/b/status/2",
            "text": "quoted",
            "created_at": "2026-05-10T23:00:00Z",
            "lang": "en",
            "favorite_count": 10,
            "retweet_count": 5,
            "reply_count": 1,
            "quote_count": 0,
            "has_media": False,
            "is_reply": False,
            "is_quote": False,
            "is_retweet": False,
            "author": {"name": "B", "handle": "b", "verified": True},
        },
    )

    assert item.media[0].alt_text == "chart"
    assert item.quoted_post is not None
    assert item.quoted_post.id == "2"
