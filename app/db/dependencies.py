from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker


def get_db_session(request: Request) -> Generator[Session]:
    """Yield a request-scoped session from this app's configured factory."""
    factory: sessionmaker[Session] | None = getattr(
        request.app.state, "db_session_factory", None
    )
    if factory is None:
        raise RuntimeError("Database session factory is not initialized")
    with factory() as session:
        yield session
