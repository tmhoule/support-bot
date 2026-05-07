from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings
from app.db.models import Base


_engine_cache: dict[str, object] = {}
_session_cache: dict[str, sessionmaker] = {}


def _engine():
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{settings.data_dir}/app.db"
    if url not in _engine_cache:
        eng = create_engine(url, future=True)
        Base.metadata.create_all(eng)
        _engine_cache[url] = eng
    return _engine_cache[url]


def _session_local() -> sessionmaker:
    settings = get_settings()
    url = f"sqlite:///{settings.data_dir}/app.db"
    if url not in _session_cache:
        _session_cache[url] = sessionmaker(bind=_engine(), expire_on_commit=False, class_=Session)
    return _session_cache[url]


@contextmanager
def session_scope() -> Session:
    s = _session_local()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
