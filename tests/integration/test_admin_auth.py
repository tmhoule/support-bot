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


def test_admin_download_upload_returns_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import create_app as _create
    from app.db.session import session_scope
    from app.db.repository import ConversationRepository

    client = TestClient(_create())
    with session_scope() as s:
        convo = ConversationRepository(s).create_conversation(tech_name="Test")

    udir = tmp_path / "uploads" / convo.id
    udir.mkdir(parents=True)
    (udir / "20260508T000000-app.log").write_text("ERROR: line 1")

    r = client.get(f"/admin/conversations/{convo.id}/upload/app.log")
    assert r.status_code == 200
    assert "ERROR: line 1" in r.text
    assert "attachment" in r.headers.get("content-disposition", "").lower()


def test_admin_download_upload_404_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import create_app as _create
    from app.db.session import session_scope
    from app.db.repository import ConversationRepository

    client = TestClient(_create())
    with session_scope() as s:
        convo = ConversationRepository(s).create_conversation(tech_name="Test")

    r = client.get(f"/admin/conversations/{convo.id}/upload/ghost.log")
    assert r.status_code == 404
