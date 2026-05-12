"""Structured error payloads for twikit-mcp."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorCode(str, Enum):
    """Stable error codes returned by twikit-mcp."""

    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    INVALID_POST_URL = "INVALID_POST_URL"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    UPSTREAM_CHANGED = "UPSTREAM_CHANGED"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorPayload(BaseModel):
    """Structured machine-readable error payload."""

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None


class AuthRequiredError(PermissionError):
    """Raised when an authenticated-only tool is called in guest mode."""


def _build_error(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return ErrorPayload(
        code=code,
        message=message,
        retryable=retryable,
        details=details,
    )


def auth_required_error(
    message: str = "Authentication is required for this operation.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.AUTH_REQUIRED, message, details=details)


def auth_expired_error(
    message: str = "Stored X cookies are expired or invalid.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.AUTH_EXPIRED, message, details=details)


def invalid_post_url_error(
    message: str = "Post URL could not be parsed into a status ID.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.INVALID_POST_URL, message, details=details)


def invalid_argument_error(
    message: str = "One or more arguments are invalid.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.INVALID_ARGUMENT, message, details=details)


def rate_limited_error(
    message: str = "X rate limit reached. Retry later.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.RATE_LIMITED, message, retryable=True, details=details)


def not_found_error(
    message: str = "Requested resource was not found.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.NOT_FOUND, message, details=details)


def upstream_changed_error(
    message: str = "X or twikit behavior changed unexpectedly.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.UPSTREAM_CHANGED, message, details=details)


def partial_results_error(
    message: str = "Only partial results are available.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.PARTIAL_RESULTS, message, details=details)


def internal_error(
    message: str = "Unexpected internal error.",
    *,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    return _build_error(ErrorCode.INTERNAL_ERROR, message, details=details)
