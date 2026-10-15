from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.db.base import Base
from app.db.dependencies import get_db_session
from app.db.models import CategoryRuleSet, WhoRuleSet
from app.db.repositories import DatasetRepository
from app.main import create_app


def test_settings_reads_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    assert Settings().database_url == "sqlite:///./test.db"


def test_dataset_repository_persists_rows_and_owner() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        with factory.begin() as session:
            dataset = DatasetRepository(session).add(
                [(Decimal("12.34"), {"description": "Lunch", "amount": 12.34})],
                owner_id="user-id-placeholder",
            )
            dataset_id = dataset.id
        with factory() as session:
            loaded = DatasetRepository(session).get(
                dataset_id, owner_id="user-id-placeholder"
            )
            assert loaded is not None
            assert loaded.owner_id == "user-id-placeholder"
            assert len(loaded.rows) == 1
            assert loaded.rows[0].amount == Decimal("12.34")
            assert loaded.rows[0].values["description"] == "Lunch"
            assert (
                DatasetRepository(session).get(dataset_id, owner_id="another-user")
                is None
            )
        assert {
            "datasets",
            "expense_rows",
            "category_rule_sets",
            "who_rule_sets",
        } <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_app_database_lifecycle_and_session_dependency() -> None:
    app = create_app(app_settings=Settings(database_url="sqlite://"))
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    app.state.db_session_factory = sessionmaker(engine, class_=Session)

    async def check_lifespan() -> None:
        async with app.router.lifespan_context(app):
            assert app.state.db_session_factory is not None
            request = Request({"type": "http", "app": app})
            session_dependency = get_db_session(request)
            session = next(session_dependency)
            assert isinstance(session, Session)
            session_dependency.close()

    asyncio.run(check_lifespan())
    engine.dispose()


def test_rule_set_models_are_independent_records() -> None:
    category = CategoryRuleSet(name="Household", rules=[{"category": "Food"}])
    who = WhoRuleSet(name="Household", rules=[{"match": "description"}])
    assert category.rules != who.rules
