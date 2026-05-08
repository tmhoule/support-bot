from fastapi.testclient import TestClient
from app.main import create_app


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(create_app())


def test_admin_conversations_open_no_auth(tmp_path, monkeypatch):
    """Admin pages are intentionally open in v1 (network-trusted, anonymous);
    NetIQ SAML will gate them at the proxy layer later."""
    c = _client(tmp_path, monkeypatch)
    r = c.get("/admin/conversations")
    assert r.status_code == 200


def test_admin_indexer_status_open_no_auth(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.get("/admin/indexer-status")
    assert r.status_code == 200
