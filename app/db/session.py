from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    """Create an engine and session factory for one application instance."""
    engine = create_engine(database_url, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
