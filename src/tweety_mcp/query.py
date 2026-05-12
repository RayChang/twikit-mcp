"""Search query composition helpers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from tweety_mcp.normalize import NormalizationError, normalize_author


TwikitSearchMode = Literal["Latest", "Top", "Media"]


class QueryError(ValueError):
    """Raised when search query parameters are invalid."""


def compose_search_query(
    *,
    query: str,
    author: str | None = None,
    since: str | None = None,
    until: str | None = None,
    lang: str | None = None,
) -> str:
    """Compose the internal X search query from structured tool parameters."""
    normalized_query = query.strip()
    if not normalized_query:
        raise QueryError("query must not be empty")

    _validate_time_range(since=since, until=until)

    parts = [normalized_query]
    if author is not None:
        try:
            parts.append(f"from:{normalize_author(author)}")
        except NormalizationError as exc:
            raise QueryError(str(exc)) from exc
    if since is not None:
        parts.append(f"since:{_validate_date_filter('since', since)}")
    if until is not None:
        parts.append(f"until:{_validate_date_filter('until', until)}")
    if lang is not None:
        parts.append(f"lang:{_validate_lang(lang)}")

    return " ".join(parts)


def normalize_sort(sort: str | None) -> TwikitSearchMode:
    """Map public sort values to twikit search mode names."""
    if sort is None:
        return "Latest"

    match sort.lower():
        case "latest":
            return "Latest"
        case "top":
            return "Top"
        case "media":
            return "Media"
        case _:
            raise QueryError("sort must be one of: latest, top, media")


def _validate_time_range(*, since: str | None, until: str | None) -> None:
    if since is None or until is None:
        return

    try:
        parsed_since = _parse_date_filter(since)
        parsed_until = _parse_date_filter(until)
    except ValueError as exc:
        raise QueryError("since and until must be YYYY-MM-DD or ISO 8601") from exc

    if parsed_since > parsed_until:
        raise QueryError("since must be earlier than or equal to until")


def _validate_date_filter(name: str, value: str) -> str:
    try:
        parsed_date = _parse_date_filter(value)
    except ValueError as exc:
        raise QueryError(f"{name} must be YYYY-MM-DD or ISO 8601") from exc
    return parsed_date.isoformat()


def _parse_date_filter(value: str) -> date:
    candidate = value.strip()
    if not candidate:
        raise ValueError("empty date")
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    if "T" in candidate:
        return datetime.fromisoformat(candidate).date()
    return date.fromisoformat(candidate)


def _validate_lang(lang: str) -> str:
    candidate = lang.strip().lower()
    if not candidate or not candidate.replace("-", "").isalpha():
        raise QueryError("lang must be a language code")
    return candidate
