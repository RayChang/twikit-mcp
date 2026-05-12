"""Mapping helpers between twikit objects and stable MCP schemas."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from tweety_mcp.cache import TTLCache
from tweety_mcp.errors import (
    AuthRequiredError,
    ErrorPayload,
    auth_expired_error,
    internal_error,
    invalid_argument_error,
    not_found_error,
    rate_limited_error,
    upstream_changed_error,
)
from tweety_mcp.models import (
    ArticlePayload,
    Author,
    BookmarkListItem,
    BookmarkListResponse,
    FullPostPayload,
    MediaItem,
    SearchPostsResponse,
    SearchPostSummary,
)
from tweety_mcp.normalize import NormalizationError, extract_post_id, normalize_author
from tweety_mcp.query import QueryError, compose_search_query, normalize_sort


DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_BOOKMARK_SCAN_PAGES = 5


class SearchService:
    """Search posts through a twikit-compatible client."""

    def __init__(
        self,
        *,
        client: Any,
        cursor_cache: TTLCache[Any] | None = None,
    ) -> None:
        self._client = client
        self._cursor_cache = cursor_cache or TTLCache(default_ttl_seconds=120)
        self._client_activated = False

    async def search_posts(
        self,
        *,
        query: str,
        author: str | None = None,
        sort: str | None = None,
        since: str | None = None,
        until: str | None = None,
        lang: str | None = None,
        limit: int = DEFAULT_LIMIT,
        cursor: str | None = None,
    ) -> SearchPostsResponse:
        if limit < 1 or limit > MAX_LIMIT:
            raise QueryError(f"limit must be between 1 and {MAX_LIMIT}")

        if cursor is None:
            await _activate_client_if_supported(self._client, activated=self._client_activated)
            self._client_activated = True
            search_query = compose_search_query(
                query=query,
                author=author,
                since=since,
                until=until,
                lang=lang,
            )
            result = await self._client.search_tweet(search_query, normalize_sort(sort))
        else:
            previous_result = self._cursor_cache.get(cursor)
            if previous_result is None:
                raise QueryError("cursor is unknown or expired")
            result = await previous_result.next()

        return self._map_search_result(result=result, limit=limit)

    def _map_search_result(self, *, result: Any, limit: int) -> SearchPostsResponse:
        items = [map_tweet_to_search_summary(tweet) for tweet in list(result)[:limit]]
        next_cursor = _optional_string(
            _get_optional(result, "next_cursor") or _get_optional(result, "cursor")
        )
        if next_cursor:
            self._cursor_cache.set(next_cursor, result)
        return SearchPostsResponse(items=items, next_cursor=next_cursor)


class PostService:
    """Fetch and map individual posts through a twikit-compatible client."""

    def __init__(self, *, client: Any) -> None:
        self._client = client
        self._client_activated = False

    async def get_post(self, *, url: str | None = None, id: str | None = None) -> FullPostPayload:
        if (url is None and id is None) or (url is not None and id is not None):
            raise QueryError("provide exactly one of url or id")

        try:
            post_id = extract_post_id(id if id is not None else url or "")
        except NormalizationError as exc:
            raise QueryError(str(exc)) from exc

        await _activate_client_if_supported(self._client, activated=self._client_activated)
        self._client_activated = True
        tweet = await self._client.get_tweet_by_id(post_id)
        return map_tweet_to_full_post(tweet)


class ArticleService:
    """Fetch X long-form articles attached to a tweet."""

    def __init__(self, *, client: Any) -> None:
        self._client = client
        self._client_activated = False

    async def get_article(self, *, url: str | None = None, id: str | None = None) -> ArticlePayload:
        if (url is None and id is None) or (url is not None and id is not None):
            raise QueryError("provide exactly one of url or id")

        try:
            post_id = extract_post_id(id if id is not None else url or "")
        except NormalizationError as exc:
            raise QueryError(str(exc)) from exc

        await _activate_client_if_supported(self._client, activated=self._client_activated)
        self._client_activated = True
        tweet = await self._client.get_tweet_by_id(post_id)
        article = _get_optional(tweet, "article")
        if article is None:
            raise QueryError("this post does not contain a long-form article")
        return map_article_to_payload(article=article, tweet=tweet)


class BookmarkService:
    """Fetch authenticated bookmarks and apply bounded local filters."""

    def __init__(
        self,
        *,
        client: Any,
        authenticated: bool,
        cursor_cache: TTLCache[Any] | None = None,
    ) -> None:
        self._client = client
        self._authenticated = authenticated
        self._cursor_cache = cursor_cache or TTLCache(default_ttl_seconds=120)
        self._client_activated = False

    async def get_bookmarks(
        self,
        *,
        query: str | None = None,
        author: str | None = None,
        since: str | None = None,
        until: str | None = None,
        lang: str | None = None,
        limit: int = DEFAULT_LIMIT,
        cursor: str | None = None,
    ) -> BookmarkListResponse:
        if not self._authenticated:
            raise AuthRequiredError("Bookmarks require cookie-auth mode")
        if limit < 1 or limit > MAX_LIMIT:
            raise QueryError(f"limit must be between 1 and {MAX_LIMIT}")
        filters = _BookmarkFilters(query=query, author=author, since=since, until=until, lang=lang)
        max_pages = MAX_BOOKMARK_SCAN_PAGES if filters.enabled else 1
        if cursor is None:
            await _activate_client_if_supported(self._client, activated=self._client_activated)
            self._client_activated = True
            result = await self._client.get_bookmarks(count=limit)
        else:
            previous_result = self._cursor_cache.get(cursor)
            if previous_result is None:
                raise QueryError("cursor is unknown or expired")
            result = await previous_result.next()
        items: list[BookmarkListItem] = []
        scanned_pages = 0
        next_cursor: str | None = None

        while result is not None and scanned_pages < max_pages and len(items) < limit:
            scanned_pages += 1
            next_cursor = _optional_string(
                _get_optional(result, "next_cursor") or _get_optional(result, "cursor")
            )
            if next_cursor:
                self._cursor_cache.set(next_cursor, result)
            for tweet in result:
                summary = map_tweet_to_search_summary(tweet)
                item = BookmarkListItem(**summary.model_dump())
                if filters.matches(item):
                    items.append(item)
                    if len(items) >= limit:
                        break
            if len(items) >= limit or scanned_pages >= max_pages or not next_cursor:
                break
            result = await result.next()

        partial = filters.enabled and bool(next_cursor) and scanned_pages >= max_pages
        return BookmarkListResponse(
            items=items,
            next_cursor=next_cursor,
            partial=partial,
            scanned_pages=scanned_pages,
        )


class _BookmarkFilters:
    def __init__(
        self,
        *,
        query: str | None,
        author: str | None,
        since: str | None,
        until: str | None,
        lang: str | None,
    ) -> None:
        self.query = query.strip().lower() if query else None
        try:
            self.author = normalize_author(author) if author else None
        except NormalizationError as exc:
            raise QueryError(str(exc)) from exc
        self.since = _parse_date_boundary("since", since) if since else None
        self.until = _parse_date_boundary("until", until) if until else None
        if self.since is not None and self.until is not None and self.since > self.until:
            raise QueryError("since must be earlier than or equal to until")
        self.lang = lang.strip().lower() if lang else None
        self.enabled = any(
            value is not None
            for value in (self.query, self.author, self.since, self.until, self.lang)
        )

    def matches(self, item: BookmarkListItem) -> bool:
        created_date = _parse_date_boundary("created_at", item.created_at)
        return all(
            (
                self.query is None or self.query in item.text.lower(),
                self.author is None or self.author == item.author.handle,
                self.since is None or created_date >= self.since,
                self.until is None or created_date <= self.until,
                self.lang is None or self.lang == item.lang.lower(),
            )
        )


def map_tweet_to_search_summary(tweet: Any) -> SearchPostSummary:
    """Map a tweet-like object (twikit or tweety) into a listing-friendly schema."""
    author = _map_author(_get_required_one_of(tweet, ("user", "author")))
    tweet_id = str(_get_required(tweet, "id"))

    is_reply = _coerce_bool(
        _get_optional(tweet, "is_reply"),
        _get_optional(tweet, "in_reply_to_status_id") is not None,
    )
    is_quote = _coerce_bool(
        _get_optional(tweet, "is_quoted"),
        _get_optional(tweet, "quote") is not None
        or _get_optional(tweet, "quoted_tweet") is not None,
    )
    is_retweet = _coerce_bool(
        _get_optional(tweet, "is_retweet"),
        _get_optional(tweet, "retweeted_tweet") is not None,
    )

    return SearchPostSummary(
        id=tweet_id,
        url=f"https://x.com/{author.handle}/status/{tweet_id}",
        text=str(_get_required_one_of(tweet, ("text", "tweet_body"))),
        created_at=_get_required_one_of(tweet, ("created_at", "created_on", "date")),
        lang=str(_get_optional_one_of(tweet, ("lang", "language"), "")),
        favorite_count=_get_count_one_of(tweet, ("favorite_count", "likes")),
        retweet_count=_get_count_one_of(tweet, ("retweet_count", "retweet_counts")),
        reply_count=_get_count_one_of(tweet, ("reply_count", "reply_counts")),
        quote_count=_get_count_one_of(tweet, ("quote_count", "quote_counts")),
        has_media=bool(_get_optional(tweet, "media", [])),
        is_reply=is_reply,
        is_quote=is_quote,
        is_retweet=is_retweet,
        author=author,
    )


def map_tweet_to_full_post(tweet: Any) -> FullPostPayload:
    """Map a tweet-like object (twikit or tweety) into a full LLM analysis schema."""
    summary = map_tweet_to_search_summary(tweet)
    quoted_tweet = _get_optional(tweet, "quote") or _get_optional(tweet, "quoted_tweet")
    retweeted_tweet = _get_optional(tweet, "retweeted_tweet")

    return FullPostPayload(
        **summary.model_dump(),
        view_count=_get_optional_one_of(tweet, ("view_count", "views")),
        hashtags=list(_iter_string_values(_get_optional(tweet, "hashtags", []))),
        urls=list(_iter_url_strings(_get_optional(tweet, "urls", []))),
        mentions=list(_iter_string_values(
            _get_optional_one_of(tweet, ("mentions", "user_mentions"), [])
        )),
        media=[_map_media_item(item) for item in _get_optional(tweet, "media", [])],
        in_reply_to_status_id=_optional_string(_get_optional(tweet, "in_reply_to_status_id")),
        in_reply_to_user_handle=_map_reply_user_handle(_get_optional(tweet, "in_reply_to_user")),
        quoted_post=map_tweet_to_search_summary(quoted_tweet) if quoted_tweet is not None else None,
        retweeted_post=map_tweet_to_search_summary(retweeted_tweet) if retweeted_tweet is not None else None,
    )


def map_article_to_payload(*, article: Any, tweet: Any) -> ArticlePayload:
    """Map a tweety ``Article`` plus its owning tweet into an ``ArticlePayload``."""
    author = _map_author(_get_required_one_of(tweet, ("user", "author")))
    article_id = str(_get_required(article, "id"))
    title = str(_get_optional(article, "title") or "")
    body_text = str(_get_optional_one_of(article, ("text", "plain_text"), ""))
    cover_media = _map_article_media(_get_optional(article, "cover_media"))
    article_media = [
        item
        for item in (
            _map_article_media(raw)
            for raw in (_get_optional(article, "media", []) or [])
        )
        if item is not None
    ]
    return ArticlePayload(
        id=article_id,
        url=f"https://x.com/i/article/{article_id}",
        title=title,
        preview_text=_optional_string(_get_optional(article, "preview_text")),
        text=body_text,
        created_at=_get_required_one_of(tweet, ("created_at", "created_on", "date")),
        author=author,
        cover_media=cover_media,
        media=article_media,
    )


_ARTICLE_MEDIA_TYPE_BY_CLASS = {
    "ApiImage": "photo",
    "ApiVideo": "video",
    "ApiGif": "animated_gif",
}


def _map_article_media(item: Any) -> MediaItem | None:
    """Convert a tweety article media object (ApiImage/ApiVideo/ApiGif) to MediaItem."""
    if item is None:
        return None
    preview = _get_optional(item, "preview_image")
    source = preview if preview is not None else item
    url = _get_optional_one_of(source, ("direct_url", "media_url_https", "url"), "")
    if not url:
        return None
    media_type = _ARTICLE_MEDIA_TYPE_BY_CLASS.get(type(item).__name__) or str(
        _get_optional(item, "type", "")
    )
    return MediaItem(
        type=media_type,
        url=str(url),
        alt_text=_optional_string(_get_optional(item, "alt_text")),
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
        url=str(
            _get_optional(media, "media_url_https")
            or _get_optional(media, "direct_url")
            or _get_optional(media, "url")
            or _get_optional(media, "media_url")
            or ""
        ),
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
            text = (
                _get_optional(value, "text")
                or _get_optional(value, "screen_name")
                or _get_optional(value, "username")
                or _get_optional(value, "url")
            )
            if text is not None:
                yield str(text)


def _iter_url_strings(values: Iterable[Any]) -> Iterable[str]:
    """Yield canonical URLs preferring expanded forms when available."""
    for value in values:
        if isinstance(value, str):
            yield value
            continue
        text = (
            _get_optional(value, "expanded_url")
            or _get_optional(value, "url")
            or _get_optional(value, "display_url")
        )
        if text is not None:
            yield str(text)


def _get_required(obj: Any, name: str) -> Any:
    value = _get_optional(obj, name)
    if value is None:
        raise ValueError(f"tweet is missing required field: {name}")
    return value


def _get_required_one_of(obj: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        value = _get_optional(obj, name)
        if value is not None:
            return value
    raise ValueError(f"tweet is missing required field: any of {names}")


def _get_optional(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _get_optional_one_of(obj: Any, names: tuple[str, ...], default: Any = None) -> Any:
    for name in names:
        value = _get_optional(obj, name)
        if value is not None:
            return value
    return default


def _get_count(obj: Any, name: str) -> int:
    value = _get_optional(obj, name, 0)
    return int(value or 0)


def _get_count_one_of(obj: Any, names: tuple[str, ...]) -> int:
    for name in names:
        value = _get_optional(obj, name)
        if value is not None:
            return int(value or 0)
    return 0


def _coerce_bool(primary: Any, fallback: bool) -> bool:
    if primary is None:
        return fallback
    return bool(primary)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_date_boundary(name: str, value: str) -> date:
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        if "T" in candidate:
            return datetime.fromisoformat(candidate).date()
        return date.fromisoformat(candidate)
    except ValueError as exc:
        raise QueryError(f"{name} must be YYYY-MM-DD or ISO 8601") from exc


async def _activate_client_if_supported(client: Any, *, activated: bool) -> None:
    if activated:
        return
    activate = getattr(client, "activate", None)
    if activate is None:
        return
    maybe_awaitable = activate()
    if hasattr(maybe_awaitable, "__await__"):
        await maybe_awaitable


def _exception_details(exc: Exception) -> dict[str, str]:
    return {"exception_type": type(exc).__name__}
