"""Authentication helpers for local cookie-based configuration."""

from dataclasses import dataclass


MIN_COOKIE_VALUE_LENGTH = 8


@dataclass(frozen=True, slots=True)
class AuthCookies:
    """Validated cookie values required for authenticated mode."""

    auth_token: str
    ct0: str


def validate_auth_cookies(auth_token: object, ct0: object) -> AuthCookies:
    """Validate cookie values locally without contacting X."""
    return AuthCookies(
        auth_token=_validate_cookie_value("auth_token", auth_token),
        ct0=_validate_cookie_value("ct0", ct0),
    )


def _validate_cookie_value(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")

    if len(value) < MIN_COOKIE_VALUE_LENGTH:
        raise ValueError(f"{name} must be at least {MIN_COOKIE_VALUE_LENGTH} characters")

    if value.strip() != value:
        raise ValueError(f"{name} must not contain leading or trailing whitespace")

    if any(character.isspace() for character in value):
        raise ValueError(f"{name} must not contain whitespace")

    return value
