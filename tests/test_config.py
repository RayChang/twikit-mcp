import json

import pytest


def test_guest_mode_when_no_cookie_sources(monkeypatch, tmp_path):
    from twikit_mcp.config import load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)

    config = load_runtime_config(config_dir=tmp_path)

    assert config.mode == "guest"


def test_env_vars_take_precedence_over_cookie_file(monkeypatch, tmp_path):
    from twikit_mcp.config import load_runtime_config

    (tmp_path / "cookies.json").write_text(
        json.dumps({"auth_token": "file-token-123", "ct0": "file-ct0-1234"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("TWIKIT_MCP_AUTH_TOKEN", "env-token-1234")
    monkeypatch.setenv("TWIKIT_MCP_CT0", "env-ct0-12345")

    config = load_runtime_config(config_dir=tmp_path)

    assert config.mode == "cookie-auth"
    assert config.auth_token == "env-token-1234"
    assert config.ct0 == "env-ct0-12345"


def test_cookie_file_is_used_when_env_is_missing(monkeypatch, tmp_path):
    from twikit_mcp.config import load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text(
        json.dumps({"auth_token": "file-token-123", "ct0": "file-ct0-1234"}),
        encoding="utf-8",
    )

    config = load_runtime_config(config_dir=tmp_path)

    assert config.mode == "cookie-auth"
    assert config.auth_token == "file-token-123"
    assert config.ct0 == "file-ct0-1234"


def test_invalid_cookie_shape_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text(
        json.dumps({"auth_token": "short", "ct0": "file-ct0-1234"}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)
