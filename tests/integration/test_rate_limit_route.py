from fastapi.testclient import TestClient
from app.main import create_app


def test_rate_limit_returns_429_after_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "2")
    import app.routes.chat as chat_module
    chat_module._limiter = None
    client = TestClient(create_app())
    r = client.post("/chat/start", data={"tech_name": "Alice"}, follow_redirects=False)
    convo_id = r.headers["location"].rsplit("/", 1)[-1]
    assert client.post(f"/chat/{convo_id}/message", data={"text": "x"}).status_code == 200
    assert client.post(f"/chat/{convo_id}/message", data={"text": "y"}).status_code == 200
    assert client.post(f"/chat/{convo_id}/message", data={"text": "z"}).status_code == 429
