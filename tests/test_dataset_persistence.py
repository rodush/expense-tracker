from __future__ import annotations

import asyncio
import csv
import sys
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.models import Dataset
from app.services.database_dataset_store import DatabaseDatasetStore
from app.services.dataset_store import DatasetNotFoundError
from app.services.upload_cache import ProcessedUploadCache
from app.services.upload_service import UploadService


def _factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'datasets.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def test_database_store_is_shared_and_preserves_cents(tmp_path) -> None:
    engine, factory = _factory(tmp_path)
    try:
        writer = DatabaseDatasetStore(factory)
        reader = DatabaseDatasetStore(factory)
        dataset_id = writer.create(
            [
                {
                    "date": "2026-07-01",
                    "amount": "10.005",
                    "description": "Lunch",
                    "who": "Roman",
                    "category": "Food",
                }
            ]
        )
        with factory() as session:
            assert session.get(Dataset, dataset_id).expires_at is None

        assert reader.get(dataset_id) == [
            {
                "date": "2026-07-01",
                "amount": 10.01,
                "description": "Lunch",
                "who": "Roman",
                "category": "Food",
            }
        ]
    finally:
        engine.dispose()


def test_database_store_retention_expires_dataset(tmp_path) -> None:
    engine, factory = _factory(tmp_path)
    try:
        store = DatabaseDatasetStore(factory)
        dataset_id = store.create([{"amount": 1.25}])
        with factory.begin() as session:
            dataset = session.get(Dataset, dataset_id)
            dataset.expires_at = datetime.now(UTC) - timedelta(days=1)

        try:
            store.get(dataset_id)
        except DatasetNotFoundError:
            pass
        else:
            raise AssertionError("expired dataset should not be available")

        with factory() as session:
            assert session.get(Dataset, dataset_id) is None
    finally:
        engine.dispose()


def test_categorized_download_can_be_rebuilt_after_file_loss(tmp_path) -> None:
    engine, factory = _factory(tmp_path)

    async def categorize(rows):
        return [{**row, "category": "Food"} for row in rows]

    try:
        store = DatabaseDatasetStore(factory)
        service = UploadService(
            dataset_store=store,
            upload_cache=ProcessedUploadCache(),
            categorize=categorize,
            determine_who=lambda _: "Roman",
            downloads_dir=tmp_path / "downloads",
        )
        payload = asyncio.run(
            service.process_upload(
                "expenses.csv",
                b"date,amount,description\n2026-07-01,-10.005,Lunch\n",
            )
        )
        expected_path = service.download_path(payload["download_id"])
        expected_path.unlink()

        restarted_service = UploadService(
            dataset_store=DatabaseDatasetStore(factory),
            upload_cache=ProcessedUploadCache(),
            categorize=categorize,
            determine_who=lambda _: "Roman",
            downloads_dir=tmp_path / "downloads",
        )
        rebuilt_path = restarted_service.download_path(payload["download_id"])
        with rebuilt_path.open(newline="") as file:
            rows = list(csv.DictReader(StringIO(file.read())))

        assert rows == [
            {
                "date": "2026-07-01",
                "amount": "10.01",
                "description": "Lunch",
                "who": "Roman",
                "category": "Food",
            }
        ]
    finally:
        engine.dispose()
