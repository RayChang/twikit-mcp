"""Factory for tweety-backed clients with a twikit-compatible surface.

The MCP services were originally built against twikit and still call
``search_tweet``/``get_tweet_by_id``/``get_bookmarks``. tweety has a
different API shape, so the factory returns a thin wrapper that bridges
those calls onto :class:`tweety.TwitterAsync`. Tests inject lightweight
fakes via ``guest_client_class`` / ``auth_client_class`` to avoid any
network or tweety dependency.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

from tweety_mcp.config import RuntimeConfig


DEFAULT_LANGUAGE = "en-US"
DEFAULT_SESSION_NAME = "tweety-mcp"
TWEETY_PAGE_SIZE = 20


class ClientFactoryError(ValueError):
    """Raised when a tweety client cannot be constructed from config."""


class _ClientClass(Protocol):
    def __call__(self, language: str) -> Any: ...


class TwikitClientFactory:
    """Create tweety-backed clients without performing network requests."""

    def __init__(
        self,
        *,
        guest_client_class: _ClientClass | None = None,
        auth_client_class: _ClientClass | None = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        if guest_client_class is None or auth_client_class is None:
            guest_client_class, auth_client_class = _load_default_client_classes(
                guest_client_class=guest_client_class,
                auth_client_class=auth_client_class,
            )
        self._guest_client_class = guest_client_class
        self._auth_client_class = auth_client_class
        self._language = language

    def create_client(self, config: RuntimeConfig) -> Any:
        if config.mode == "guest":
            return self._guest_client_class(self._language)

        if config.mode == "cookie-auth":
            if config.auth_token is None or config.ct0 is None:
                raise ClientFactoryError("cookie-auth mode requires auth_token and ct0")

            client = self._auth_client_class(self._language)
            client.set_cookies(
                {
                    "auth_token": config.auth_token,
                    "ct0": config.ct0,
                }
            )
            return client

        raise ClientFactoryError(f"unsupported runtime mode: {config.mode}")


class TweetyClient:
    """twikit-shaped wrapper around :class:`tweety.TwitterAsync`."""

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self.language = language
        self._cookies: dict[str, str] | None = None
        self._app: Any = None
        self._app_factory = _make_tweety_app

    def set_cookies(self, cookies: dict[str, str]) -> None:
        self._cookies = dict(cookies)

    async def activate(self) -> None:
        if self._app is not None:
            return
        self._app = self._app_factory(DEFAULT_SESSION_NAME)
        if self._cookies is not None:
            await self._app.load_cookies(self._cookies)
        else:
            await self._app.connect()

    async def search_tweet(
        self,
        query: str,
        sort: str | None = None,
        count: int = TWEETY_PAGE_SIZE,
        cursor: str | None = None,
    ) -> Any:
        await self.activate()
        pages = max(1, math.ceil(count / TWEETY_PAGE_SIZE))
        filter_ = _resolve_search_filter(sort)
        result = await self._app.search(
            keyword=query,
            pages=pages,
            filter_=filter_,
            cursor=cursor,
        )
        return _SearchPage(app=self._app, result=result, pages=pages, query=query, filter_=filter_)

    async def get_tweet_by_id(self, post_id: str) -> Any:
        await self.activate()
        return await self._app.tweet_detail(post_id)

    async def get_bookmarks(
        self,
        count: int = TWEETY_PAGE_SIZE,
        cursor: str | None = None,
    ) -> Any:
        await self.activate()
        pages = max(1, math.ceil(count / TWEETY_PAGE_SIZE))
        result = await self._app.get_bookmarks(pages=pages, cursor=cursor)
        return _BookmarksPage(app=self._app, result=result, pages=pages)


class _SearchPage:
    """Adapter exposing twikit's iterate-and-``next()`` shape over tweety."""

    def __init__(self, *, app: Any, result: Any, pages: int, query: str, filter_: Any) -> None:
        self._app = app
        self._result = result
        self._pages = pages
        self._query = query
        self._filter = filter_

    def __iter__(self):
        return iter(_extract_tweets(self._result))

    @property
    def next_cursor(self) -> str | None:
        return _get_attr_or_key(self._result, "cursor") or _get_attr_or_key(self._result, "cursor_top")

    async def next(self) -> "_SearchPage":
        cursor = self.next_cursor
        if not cursor:
            raise StopAsyncIteration("no further search pages")
        result = await self._app.search(
            keyword=self._query,
            pages=self._pages,
            filter_=self._filter,
            cursor=cursor,
        )
        return _SearchPage(
            app=self._app, result=result, pages=self._pages, query=self._query, filter_=self._filter
        )


class _BookmarksPage:
    """Adapter exposing twikit's iterate-and-``next()`` shape over tweety."""

    def __init__(self, *, app: Any, result: Any, pages: int) -> None:
        self._app = app
        self._result = result
        self._pages = pages

    def __iter__(self):
        return iter(_extract_tweets(self._result))

    @property
    def next_cursor(self) -> str | None:
        return _get_attr_or_key(self._result, "cursor") or _get_attr_or_key(self._result, "cursor_top")

    async def next(self) -> "_BookmarksPage":
        cursor = self.next_cursor
        if not cursor:
            raise StopAsyncIteration("no further bookmark pages")
        result = await self._app.get_bookmarks(pages=self._pages, cursor=cursor)
        return _BookmarksPage(app=self._app, result=result, pages=self._pages)


def _extract_tweets(result: Any) -> list[Any]:
    if result is None:
        return []
    for attr in ("results", "tweets"):
        value = _get_attr_or_key(result, attr)
        if value is not None:
            return list(value)
    try:
        return list(result)
    except TypeError:
        return []


def _get_attr_or_key(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _resolve_search_filter(sort: str | None) -> Any:
    """Map our public sort values to tweety's ``SearchFilters`` constants."""
    if sort is None:
        return None
    normalized = str(sort).strip().lower()
    if normalized in {"", "top"}:
        return None
    try:
        from tweety.filters import SearchFilters
    except ImportError:
        return sort
    mapping = {
        "latest": getattr(SearchFilters, "Latest", "Latest"),
        "media": getattr(SearchFilters, "Media", "Media"),
        "photos": getattr(SearchFilters, "Media", "Media"),
        "videos": getattr(SearchFilters, "Media", "Media"),
        "users": getattr(SearchFilters, "Users", "People"),
        "people": getattr(SearchFilters, "Users", "People"),
    }
    return mapping.get(normalized, sort)


def _make_tweety_app(session_name: str) -> Any:
    try:
        from tweety import TwitterAsync
    except ImportError as exc:
        raise ClientFactoryError("tweety-ns is not installed") from exc
    return TwitterAsync(session_name)


def _make_tweety_client(language: str) -> TweetyClient:
    return TweetyClient(language=language)


def _load_default_client_classes(
    *,
    guest_client_class: _ClientClass | None,
    auth_client_class: _ClientClass | None,
) -> tuple[_ClientClass, _ClientClass]:
    resolved_guest = guest_client_class or _make_tweety_client
    resolved_auth = auth_client_class or _make_tweety_client
    return resolved_guest, resolved_auth
