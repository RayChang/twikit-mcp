def test_logging_redacts_auth_token():
    from twikit_mcp.logging_utils import redact_secrets

    redacted = redact_secrets({"auth_token": "secret"})

    assert redacted["auth_token"] == "***REDACTED***"


def test_logging_redacts_nested_cookie_values():
    from twikit_mcp.logging_utils import redact_secrets

    redacted = redact_secrets({"headers": {"Cookie": "auth_token=secret; ct0=secret"}})

    assert redacted["headers"]["Cookie"] == "***REDACTED***"


def test_logging_leaves_safe_values_unchanged():
    from twikit_mcp.logging_utils import redact_secrets

    redacted = redact_secrets({"query": "Taylor Swift", "limit": 20})

    assert redacted == {"query": "Taylor Swift", "limit": 20}
