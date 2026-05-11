"""Factory for twikit guest and authenticated clients."""

from __future__ import annotations

from typing import Any, Protocol

from twikit_mcp.config import RuntimeConfig


DEFAULT_LANGUAGE = "en-US"


class ClientFactoryError(ValueError):
    """Raised when a twikit client cannot be constructed from config."""


class _ClientClass(Protocol):
    def __call__(self, language: str) -> Any: ...


class TwikitClientFactory:
    """Create twikit clients without performing network requests."""

    def __init__(
        self,
        *,
        guest_client_class: _ClientClass | None = None,
        auth_client_class: _ClientClass | None = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        if guest_client_class is None or auth_client_class is None:
            guest_client_class, auth_client_class = _load_twikit_client_classes(
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


def _load_twikit_client_classes(
    *,
    guest_client_class: _ClientClass | None,
    auth_client_class: _ClientClass | None,
) -> tuple[_ClientClass, _ClientClass]:
    if guest_client_class is None:
        try:
            from twikit.guest import GuestClient
        except ImportError as exc:
            raise ClientFactoryError("twikit guest client is not installed") from exc
        guest_client_class = GuestClient

    if auth_client_class is None:
        try:
            from twikit import Client
        except ImportError as exc:
            raise ClientFactoryError("twikit auth client is not installed") from exc
        auth_client_class = Client

    return guest_client_class, auth_client_class
