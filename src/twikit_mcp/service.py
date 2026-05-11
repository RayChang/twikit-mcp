"""Mapping helpers between twikit objects and stable MCP schemas."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from twikit_mcp.errors import (
    ErrorPayload,
    auth_expired_error,
    internal_error,
    invalid_argument_error,
    not_found_error,
    rate_limited_error,
    upstream_changed_error,
)
from twikit_mcp.models import Author, FullPostPayload, MediaItem, SearchPostSummary


def map_tweet_to_search_summary(tweet: Any) -> SearchPostSummary:
    """Map a twikit tweet-like object into a listing-friendly schema."""
    author = _map_author(_get_required(tweet, "user"))
    tweet_id = str(_get_required(tweet, "id"))

    return SearchPostSummary(
        id=tweet_id,
        url=f"https://x.com/{author.handle}/status/{tweet_id}",
        text=str(_get_required(tweet, "text")),
        created_at=_get_required(tweet, "created_at"),
        lang=str(_get_optional(tweet, "lang", "")),
        favorite_count=_get_count(tweet, "favorite_count"),
        retweet_count=_get_count(tweet, "retweet_count"),
        reply_count=_get_count(tweet, "reply_count"),
        quote_count=_get_count(tweet, "quote_count"),
        has_media=bool(_get_optional(tweet, "media", [])),
        is_reply=_get_optional(tweet, "in_reply_to_status_id") is not None,
        is_quote=_get_optional(tweet, "quote") is not None or _get_optional(tweet, "quoted_tweet") is not None,
        is_retweet=_get_optional(tweet, "retweeted_tweet") is not None,
        author=author,
    )


def map_tweet_to_full_post(tweet: Any) -> FullPostPayload:
    """Map a twikit tweet-like object into a full LLM analysis schema."""
    summary = map_tweet_to_search_summary(tweet)
    quoted_tweet = _get_optional(tweet, "quote") or _get_optional(tweet, "quoted_tweet")
    retweeted_tweet = _get_optional(tweet, "retweeted_tweet")

    return FullPostPayload(
        **summary.model_dump(),
        view_count=_get_optional(tweet, "view_count"),
        hashtags=list(_iter_string_values(_get_optional(tweet, "hashtags", []))),
        urls=list(_iter_string_values(_get_optional(tweet, "urls", []))),
        mentions=list(_iter_string_values(_get_optional(tweet, "mentions", []))),
        media=[_map_media_item(item) for item in _get_optional(tweet, "media", [])],
        in_reply_to_status_id=_optional_string(_get_optional(tweet, "in_reply_to_status_id")),
        in_reply_to_user_handle=_map_reply_user_handle(_get_optional(tweet, "in_reply_to_user")),
        quoted_post=map_tweet_to_search_summary(quoted_tweet) if quoted_tweet is not None else None,
        retweeted_post=map_tweet_to_search_summary(retweeted_tweet) if retweeted_tweet is not None else None,
    )


def map_exception_to_error(exc: Exception) -> ErrorPayload:
    """Map upstream/service exceptions into stable error payloads."""
    message = str(exc)
    lowered = message.lower()

    if "rate" in lowered and "limit" in lowered:
        return rate_limited_error(message=message, details=_exception_details(exc))
    if any(token in lowered for token in ("401", "403", "unauthorized", "forbidden", "auth")):
        return auth_expired_error(message=message, details=_exception_details(exc))
    if any(token in lowered for token in ("not found", "404", "deleted")):
        return not_found_error(message=message, details=_exception_details(exc))
    if any(token in lowered for token in ("invalid", "argument")):
        return invalid_argument_error(message=message, details=_exception_details(exc))
    if any(token in lowered for token in ("upstream", "parse", "schema", "structure")):
        return upstream_changed_error(message=message, details=_exception_details(exc))
    return internal_error(message=message or "Unexpected internal error.", details=_exception_details(exc))


def _map_author(user: Any) -> Author:
    handle = _get_optional(user, "screen_name") or _get_optional(user, "handle")
    if handle is None:
        raise ValueError("tweet user is missing required handle")
    return Author(
        name=str(_get_optional(user, "name", "")),
        handle=str(handle),
        verified=bool(_get_optional(user, "verified", False)),
    )


def _map_media_item(media: Any) -> MediaItem:
    return MediaItem(
        type=str(_get_optional(media, "type", "")),
        url=str(_get_optional(media, "url") or _get_optional(media, "media_url", "")),
        alt_text=_optional_string(_get_optional(media, "alt_text")),
    )


def _map_reply_user_handle(user: Any) -> str | None:
    if user is None:
        return None
    return _optional_string(_get_optional(user, "screen_name") or _get_optional(user, "handle"))


def _iter_string_values(values: Iterable[Any]) -> Iterable[str]:
    for value in values:
        if isinstance(value, str):
            yield value
        else:
            text = _get_optional(value, "text") or _get_optional(value, "url") or _get_optional(value, "screen_name")
            if text is not None:
                yield str(text)


def _get_required(obj: Any, name: str) -> Any:
    value = _get_optional(obj, name)
    if value is None:
        raise ValueError(f"tweet is missing required field: {name}")
    return value


def _get_optional(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _get_count(obj: Any, name: str) -> int:
    value = _get_optional(obj, name, 0)
    return int(value or 0)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _exception_details(exc: Exception) -> dict[str, str]:
    return {"exception_type": type(exc).__name__}
