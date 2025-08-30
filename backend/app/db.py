from __future__ import annotations

from contextlib import asynccontextmanager
import time
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import socket
from sqlmodel import SQLModel, create_engine, Session

from .settings import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def init_db() -> None:
    # Retry to allow Postgres to become reachable in containers
    last_err: Exception | None = None
    host = settings.postgres_host
    # First, wait for DNS to resolve
    for _ in range(30):
        try:
            socket.getaddrinfo(host, 5432)
            break
        except socket.gaierror as e:
            last_err = e
            time.sleep(1)
    # Then, wait for DB to accept connections
    for _ in range(60):
        try:
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError as e:
            last_err = e
            time.sleep(1)
    if last_err:
        # Do not raise to avoid crashing server; endpoints can retry
        return


def ensure_db() -> None:
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass


def get_session() -> Session:
    # Simple, robust dependency: open a session, try a lightweight ping, and yield.
    with Session(engine) as session:
        try:
            session.exec(text("SELECT 1"))
        except Exception:
            # Let route logic handle transient DB readiness; do not raise here
            pass
        yield session
