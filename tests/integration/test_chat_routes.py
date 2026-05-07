from fastapi.testclient import TestClient
from app.main import create_app


def test_get_chat_root_shows_name_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    assert "name" in r.text.lower()


def test_start_chat_redirects_to_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    client = TestClient(create_app())
    r = client.post("/chat/start", data={"tech_name": "Alice"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"].startswith("/chat/")
