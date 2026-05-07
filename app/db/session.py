from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings


def _engine():
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{settings.data_dir}/app.db"
    return create_engine(url, future=True)


_SessionLocal = sessionmaker(bind=_engine(), expire_on_commit=False, class_=Session)


@contextmanager
def session_scope() -> Session:
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
