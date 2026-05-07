import os
import tempfile

# Ensure required env vars are present at import time so that modules which
# instantiate Settings on import (e.g. app.main) succeed during test collection.
_TEST_ENV_DEFAULTS = {
    "LITELLM_BASE_URL": "x",
    "LITELLM_API_KEY": "x",
    "LITELLM_CHAT_MODEL": "x",
    "LITELLM_EMBEDDING_MODEL": "x",
    "GITHUB_REPO_URL": "x",
    "GITHUB_TOKEN": "x",
    "ADMIN_TOKEN": "x",
    "SESSION_SECRET": "x" * 32,
    "DATA_DIR": tempfile.mkdtemp(prefix="support-bot-test-"),
}

for _k, _v in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base


@pytest.fixture
def db_session(tmp_path, monkeypatch) -> Session:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine, expire_on_commit=False)
    s = sm()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LITELLM_BASE_URL", "x")
    monkeypatch.setenv("LITELLM_API_KEY", "x")
    monkeypatch.setenv("LITELLM_CHAT_MODEL", "x")
    monkeypatch.setenv("LITELLM_EMBEDDING_MODEL", "x")
    monkeypatch.setenv("GITHUB_REPO_URL", "x")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)
