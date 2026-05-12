"""Shared Pydantic schemas for tweety-mcp."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_iso_utc_timestamp(value: object) -> str:
    """Normalize supported timestamp inputs into ISO 8601 UTC with ``Z``."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError("timestamp must be a valid ISO 8601 string") from exc
    else:
        raise TypeError("timestamp must be a datetime or ISO 8601 string")

    if dt.tzinfo is None:
        raise ValueError("timestamp must include a timezone offset")

    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class ModelBase(BaseModel):
    """Base model configuration for shared schemas."""

    model_config = ConfigDict(extra="forbid")


class Author(ModelBase):
    """Minimal stable author identity fields."""

    name: str
    handle: str
    verified: bool = False


class TimestampedModel(ModelBase):
    """Base schema for payloads that expose a created timestamp."""

    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_created_at(cls, value: object) -> str:
        return normalize_iso_utc_timestamp(value)


class SearchPostSummary(TimestampedModel):
    """Listing-friendly search summary for a single post."""

    id: str
    url: str
    text: str
    lang: str
    favorite_count: int = Field(ge=0)
    retweet_count: int = Field(ge=0)
    reply_count: int = Field(ge=0)
    quote_count: int = Field(ge=0)
    has_media: bool
    is_reply: bool
    is_quote: bool
    is_retweet: bool
    author: Author


class BookmarkListItem(SearchPostSummary):
    """Bookmark listing item schema."""


class MediaItem(ModelBase):
    """Compact media metadata for full post inspection."""

    type: str
    url: str
    alt_text: str | None = None


class FullPostPayload(SearchPostSummary):
    """LLM-friendly full single-post payload."""

    view_count: int | None = Field(default=None, ge=0)
    hashtags: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    media: list[MediaItem] = Field(default_factory=list)
    in_reply_to_status_id: str | None = None
    in_reply_to_user_handle: str | None = None
    quoted_post: SearchPostSummary | None = None
    retweeted_post: SearchPostSummary | None = None


class ArticlePayload(TimestampedModel):
    """LLM-friendly long-form article payload."""

    id: str
    url: str
    title: str
    preview_text: str | None = None
    text: str
    author: Author
    cover_media: MediaItem | None = None
    media: list[MediaItem] = Field(default_factory=list)


T = TypeVar("T")


class ListResponse(ModelBase, Generic[T]):
    """Cursor-based list response wrapper."""

    items: list[T]
    next_cursor: str | None = None
    partial: bool = False


class SearchPostsResponse(ListResponse[SearchPostSummary]):
    """Response schema for post search results."""


class BookmarkListResponse(ListResponse[BookmarkListItem]):
    """Response schema for bookmark listings."""

    scanned_pages: int = Field(default=0, ge=0)


class CommentItem(SearchPostSummary):
    """A single top-level reply to a post."""


class CommentListResponse(ListResponse[CommentItem]):
    """Response schema for tweet comment listings."""
