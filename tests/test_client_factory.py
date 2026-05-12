from tweety_mcp.config import RuntimeConfig


class FakeGuestClient:
    def __init__(self, language):
        self.language = language


class FakeAuthClient:
    def __init__(self, language):
        self.language = language
        self.cookies = None

    def set_cookies(self, cookies):
        self.cookies = cookies


def test_client_factory_builds_guest_client():
    from tweety_mcp.client_factory import TwikitClientFactory

    factory = TwikitClientFactory(
        guest_client_class=FakeGuestClient,
        auth_client_class=FakeAuthClient,
    )
    config = RuntimeConfig(
        mode="guest",
        config_dir=".",
        cookies_path="./cookies.json",
    )

    client = factory.create_client(config)

    assert isinstance(client, FakeGuestClient)
    assert client.language == "en-US"


def test_client_factory_builds_authenticated_client_with_cookies():
    from tweety_mcp.client_factory import TwikitClientFactory

    factory = TwikitClientFactory(
        guest_client_class=FakeGuestClient,
        auth_client_class=FakeAuthClient,
    )
    config = RuntimeConfig(
        mode="cookie-auth",
        config_dir=".",
        cookies_path="./cookies.json",
        auth_token="auth-token-123",
        ct0="ct0-token-123",
    )

    client = factory.create_client(config)

    assert isinstance(client, FakeAuthClient)
    assert client.cookies == {"auth_token": "auth-token-123", "ct0": "ct0-token-123"}


def test_client_factory_rejects_auth_config_without_cookies():
    import pytest

    from tweety_mcp.client_factory import ClientFactoryError, TwikitClientFactory

    factory = TwikitClientFactory(
        guest_client_class=FakeGuestClient,
        auth_client_class=FakeAuthClient,
    )
    config = RuntimeConfig(
        mode="cookie-auth",
        config_dir=".",
        cookies_path="./cookies.json",
    )

    with pytest.raises(ClientFactoryError):
        factory.create_client(config)
