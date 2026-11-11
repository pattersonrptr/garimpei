"""Tests for src/config/proxy.py."""

from unittest.mock import patch

import pytest

from src.config.proxy import ProxyConfig, load_proxy_config

# ---------------------------------------------------------------------------
# ProxyConfig dataclass
# ---------------------------------------------------------------------------


class TestProxyConfig:
    def test_to_playwright_proxy_full(self):
        cfg = ProxyConfig(server="http://proxy:8080", username="u", password="p")
        result = cfg.to_playwright_proxy()
        assert result == {
            "server": "http://proxy:8080",
            "username": "u",
            "password": "p",
        }

    def test_to_playwright_proxy_no_auth(self):
        cfg = ProxyConfig(server="http://proxy:8080")
        result = cfg.to_playwright_proxy()
        assert result == {"server": "http://proxy:8080"}
        assert "username" not in result
        assert "password" not in result

    def test_to_playwright_proxy_username_only(self):
        cfg = ProxyConfig(server="http://proxy:8080", username="u")
        result = cfg.to_playwright_proxy()
        assert result["username"] == "u"
        assert "password" not in result

    def test_frozen(self):
        cfg = ProxyConfig(server="http://proxy:8080")
        with pytest.raises(AttributeError):
            cfg.server = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_proxy_config
# ---------------------------------------------------------------------------


class TestLoadProxyConfig:
    """Every test clears the environment: a local .env (even its placeholder
    values) must not leak into the expectations."""

    @patch.dict("os.environ", {}, clear=True)
    def test_disabled_by_default(self):
        assert load_proxy_config() is None

    @patch.dict(
        "os.environ",
        {"PROXY_ENABLED": "false", "PROXY_SERVER": "http://proxy:8080"},
        clear=True,
    )
    def test_disabled_explicitly(self):
        assert load_proxy_config() is None

    @patch.dict(
        "os.environ",
        {"PROXY_ENABLED": "true", "PROXY_SERVER": "http://proxy:8080"},
        clear=True,
    )
    def test_enabled_without_auth(self):
        cfg = load_proxy_config()
        assert cfg is not None
        assert cfg.server == "http://proxy:8080"
        assert cfg.username is None
        assert cfg.password is None

    @patch.dict(
        "os.environ",
        {
            "PROXY_ENABLED": "1",
            "PROXY_SERVER": "http://proxy:8080",
            "PROXY_USERNAME": "user",
            "PROXY_PASSWORD": "pass",
        },
        clear=True,
    )
    def test_enabled_with_auth(self):
        cfg = load_proxy_config()
        assert cfg is not None
        assert cfg.server == "http://proxy:8080"
        assert cfg.username == "user"
        assert cfg.password == "pass"

    @patch.dict(
        "os.environ",
        {"PROXY_ENABLED": "yes", "PROXY_SERVER": "http://proxy:8080"},
        clear=True,
    )
    def test_accepts_yes(self):
        assert load_proxy_config() is not None

    @patch.dict(
        "os.environ",
        {"PROXY_ENABLED": "true", "PROXY_SERVER": ""},
        clear=True,
    )
    def test_enabled_but_no_server_returns_none(self):
        assert load_proxy_config() is None

    @patch.dict(
        "os.environ",
        {
            "PROXY_ENABLED": "true",
            "PROXY_SERVER": "  http://proxy:8080  ",
            "PROXY_USERNAME": "  user  ",
            "PROXY_PASSWORD": "  pass  ",
        },
        clear=True,
    )
    def test_strips_whitespace(self):
        cfg = load_proxy_config()
        assert cfg is not None
        assert cfg.server == "http://proxy:8080"
        assert cfg.username == "user"
        assert cfg.password == "pass"
