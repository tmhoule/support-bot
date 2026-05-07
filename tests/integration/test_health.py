from fastapi.testclient import TestClient
from app.main import create_app


def test_healthz_returns_200(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LITELLM_BASE_URL", "x")
    monkeypatch.setenv("LITELLM_API_KEY", "x")
    monkeypatch.setenv("LITELLM_CHAT_MODEL", "x")
    monkeypatch.setenv("LITELLM_EMBEDDING_MODEL", "x")
    monkeypatch.setenv("GITHUB_REPO_URL", "x")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setenv("ADMIN_TOKEN", "x")
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)
    client = TestClient(create_app())
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
