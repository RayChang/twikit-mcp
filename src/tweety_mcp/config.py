"""Runtime configuration loading for tweety-mcp."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import stat
from typing import Literal

from tweety_mcp.auth import AuthCookies, validate_auth_cookies


AUTH_TOKEN_ENV_VAR = "TWEETY_MCP_AUTH_TOKEN"
CT0_ENV_VAR = "TWEETY_MCP_CT0"
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "tweety-mcp"

RuntimeMode = Literal["guest", "cookie-auth"]


class ConfigError(ValueError):
    """Raised when local configuration is malformed."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Normalized runtime configuration for the server."""

    mode: RuntimeMode
    config_dir: Path
    cookies_path: Path
    auth_token: str | None = None
    ct0: str | None = None


def load_runtime_config(
    config_dir: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> RuntimeConfig:
    """Load runtime config from local sources without network access."""
    resolved_dir = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    cookies_path = resolved_dir / "cookies.json"
    environment = environ if environ is not None else os.environ

    cookies = _load_cookies_from_env(environment)
    if cookies is None:
        cookies = _load_cookies_from_file(cookies_path)

    if cookies is None:
        return RuntimeConfig(
            mode="guest",
            config_dir=resolved_dir,
            cookies_path=cookies_path,
        )

    return RuntimeConfig(
        mode="cookie-auth",
        config_dir=resolved_dir,
        cookies_path=cookies_path,
        auth_token=cookies.auth_token,
        ct0=cookies.ct0,
    )


def _load_cookies_from_env(environ: Mapping[str, str]) -> AuthCookies | None:
    auth_token = environ.get(AUTH_TOKEN_ENV_VAR)
    ct0 = environ.get(CT0_ENV_VAR)

    if auth_token is None and ct0 is None:
        return None

    if auth_token is None or ct0 is None:
        raise ConfigError(
            f"{AUTH_TOKEN_ENV_VAR} and {CT0_ENV_VAR} must both be set for cookie-auth mode"
        )

    return _validate_cookies(auth_token=auth_token, ct0=ct0)


def _load_cookies_from_file(cookies_path: Path) -> AuthCookies | None:
    path_status = _inspect_cookie_path(cookies_path)
    if path_status is None:
        return None

    if stat.S_ISLNK(path_status.st_mode) and not _path_exists(cookies_path):
        raise ConfigError(f"{cookies_path} is not a usable regular file")

    if not _path_is_file(cookies_path):
        raise ConfigError(f"{cookies_path} is not a usable regular file")

    try:
        payload = json.loads(cookies_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Unable to decode {cookies_path} as UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {cookies_path}") from exc
    except OSError as exc:
        raise ConfigError(f"Unable to read {cookies_path}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"{cookies_path} must contain a JSON object")

    return _validate_cookies(
        auth_token=payload.get("auth_token"),
        ct0=payload.get("ct0"),
    )


def _validate_cookies(auth_token: object, ct0: object) -> AuthCookies:
    try:
        return validate_auth_cookies(auth_token=auth_token, ct0=ct0)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


def _inspect_cookie_path(cookies_path: Path) -> os.stat_result | None:
    try:
        return cookies_path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ConfigError(f"Unable to inspect {cookies_path}") from exc


def _path_exists(cookies_path: Path) -> bool:
    try:
        return cookies_path.exists()
    except OSError as exc:
        raise ConfigError(f"Unable to inspect {cookies_path}") from exc


def _path_is_file(cookies_path: Path) -> bool:
    try:
        return cookies_path.is_file()
    except OSError as exc:
        raise ConfigError(f"Unable to inspect {cookies_path}") from exc
