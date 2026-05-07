import os
from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://x")
    monkeypatch.setenv("LITELLM_API_KEY", "k")
    monkeypatch.setenv("LITELLM_CHAT_MODEL", "m")
    monkeypatch.setenv("LITELLM_EMBEDDING_MODEL", "e")
    monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/x/y")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("ADMIN_TOKEN", "a")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("WEB_SEARCH_ALLOWED_DOMAINS", "a.com,b.org")
    s = Settings()
    assert s.port == 8080
    assert s.web_search_allowed_domains == ["a.com", "b.org"]


def test_port_3000_rejected(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://x")
    monkeypatch.setenv("LITELLM_API_KEY", "k")
    monkeypatch.setenv("LITELLM_CHAT_MODEL", "m")
    monkeypatch.setenv("LITELLM_EMBEDDING_MODEL", "e")
    monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/x/y")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("ADMIN_TOKEN", "a")
    monkeypatch.setenv("SESSION_SECRET", "s" * 32)
    monkeypatch.setenv("PORT", "3000")
    import pytest
    with pytest.raises(ValueError, match="3000"):
        Settings()
