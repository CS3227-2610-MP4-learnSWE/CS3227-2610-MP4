"""One SQLAlchemy session per request; engines are cached per DATABASE_URL."""
import threading
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from auth.settings import load_settings

_engines: dict[str, Engine] = {}
_lock = threading.Lock()


def engine_for(url: str) -> Engine:
    with _lock:
        if url not in _engines:
            _engines[url] = create_engine(url, pool_pre_ping=True)
        return _engines[url]


def get_session() -> Iterator[Session]:
    """FastAPI dependency. Config errors raise 503; SQLAlchemyError is mapped to 503 in main.py."""
    settings = load_settings()
    with Session(engine_for(settings.database_url), expire_on_commit=False) as session:
        yield session


def open_session() -> Session:
    """A short-lived session for code that manages its own transactions (attempt store, set provider)."""
    return Session(engine_for(load_settings().database_url), expire_on_commit=False)
