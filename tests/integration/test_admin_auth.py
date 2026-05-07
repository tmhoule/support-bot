from fastapi.testclient import TestClient
from app.main import create_app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    return TestClient(create_app())


def test_admin_requires_token(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.get("/admin/conversations")
    assert r.status_code == 401


def test_admin_allows_with_token(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.get("/admin/conversations", headers={"X-Admin-Token": "secret-token"})
    assert r.status_code == 200
