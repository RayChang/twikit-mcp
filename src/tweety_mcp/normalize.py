"""Input normalization helpers for X identifiers and URLs."""

from __future__ import annotations

import re
from urllib.parse import urlparse


POST_ID_PATTERN = re.compile(r"^\d+$")
HANDLE_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,15}$")
SUPPORTED_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}


class NormalizationError(ValueError):
    """Raised when user input cannot be normalized safely."""


def extract_post_id(value: str) -> str:
    """Extract a numeric X post ID from a plain ID or supported post URL."""
    candidate = value.strip()
    if POST_ID_PATTERN.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in SUPPORTED_HOSTS:
        raise NormalizationError("post URL must be from x.com or twitter.com")

    parts = [part for part in parsed.path.split("/") if part]
    try:
        status_index = parts.index("status")
        post_id = parts[status_index + 1]
    except (ValueError, IndexError) as exc:
        raise NormalizationError("post URL must contain /status/<id>") from exc

    if not POST_ID_PATTERN.fullmatch(post_id):
        raise NormalizationError("post ID must be numeric")

    return post_id


def normalize_author(value: str) -> str:
    """Normalize an author handle from @handle, bare handle, or profile URL."""
    candidate = value.strip()
    if candidate.startswith("@"):
        candidate = candidate[1:]
        return _validate_handle(candidate)

    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc.lower() not in SUPPORTED_HOSTS:
            raise NormalizationError("author URL must be from x.com or twitter.com")
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise NormalizationError("author URL must include a handle")
        return _validate_handle(parts[0])

    return _validate_handle(candidate)


def _validate_handle(handle: str) -> str:
    if not HANDLE_PATTERN.fullmatch(handle):
        raise NormalizationError("author must be a handle or profile URL")
    return handle
