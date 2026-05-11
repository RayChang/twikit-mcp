import json
from pathlib import Path

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


def test_partial_env_configuration_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.setenv("TWIKIT_MCP_AUTH_TOKEN", "env-token-1234")
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


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


def test_directory_instead_of_cookie_file_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").mkdir()

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_invalid_json_syntax_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text("{bad json", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_non_object_json_payload_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_broken_cookie_symlink_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").symlink_to(tmp_path / "missing.json")

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_cookie_symlink_exists_check_error_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"auth_token": "file-token-123", "ct0": "file-ct0-1234"}), encoding="utf-8")
    (tmp_path / "cookies.json").symlink_to(target)

    original_exists = Path.exists

    def raise_permission_error(self):
        if self == tmp_path / "cookies.json":
            raise PermissionError("denied")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", raise_permission_error)

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_cookie_read_permission_error_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text(
        json.dumps({"auth_token": "file-token-123", "ct0": "file-ct0-1234"}),
        encoding="utf-8",
    )

    def raise_permission_error(self, encoding=None):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_text", raise_permission_error)

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_cookie_read_unicode_decode_error_raises_config_error(monkeypatch, tmp_path):
    from twikit_mcp.config import ConfigError, load_runtime_config

    monkeypatch.delenv("TWIKIT_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWIKIT_MCP_CT0", raising=False)
    (tmp_path / "cookies.json").write_text(
        json.dumps({"auth_token": "file-token-123", "ct0": "file-ct0-1234"}),
        encoding="utf-8",
    )

    def raise_unicode_decode_error(self, encoding=None):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(Path, "read_text", raise_unicode_decode_error)

    with pytest.raises(ConfigError):
        load_runtime_config(config_dir=tmp_path)


def test_auth_validator_rejects_whitespace():
    from twikit_mcp.auth import validate_auth_cookies

    with pytest.raises(ValueError):
        validate_auth_cookies(auth_token="token value", ct0="validct0123")
