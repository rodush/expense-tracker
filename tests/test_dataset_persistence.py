from __future__ import annotations

import asyncio
import csv
import sys
from io import StringIO
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.services.database_dataset_store import DatabaseDatasetStore
from app.services.expense_history_service import ExpenseHistoryService
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


def test_categorized_download_can_be_rebuilt_after_file_loss(tmp_path) -> None:
    engine, factory = _factory(tmp_path)

    async def categorize(rows):
        return [{**row, "category": "Food"} for row in rows]

    try:
        store = DatabaseDatasetStore(factory)
        service = UploadService(
            dataset_store=store,
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
        repeated = asyncio.run(
            restarted_service.process_upload(
                "expenses.csv",
                b"date,amount,description\n2026-07-01,-10.005,Lunch\n",
            )
        )
        assert repeated["new_transaction_count"] == 0
        assert repeated["duplicate_count"] == 1
        assert repeated["dataset_id"] == payload["dataset_id"]
    finally:
        engine.dispose()


def test_overlapping_exports_add_only_new_rows_and_history_survives_restart(
    tmp_path,
) -> None:
    engine, factory = _factory(tmp_path)
    categorized: list[str] = []
    resolved_people: list[str] = []

    async def categorize(rows):
        categorized.extend(str(row["description"]) for row in rows)
        return [
            {
                **row,
                "category": "Transport"
                if "train" in str(row["description"]).casefold()
                else "Food",
            }
            for row in rows
        ]

    try:
        store = DatabaseDatasetStore(factory)
        service = UploadService(
            dataset_store=store,
            categorize=categorize,
            determine_who=lambda description: (
                resolved_people.append(description) or "Household"
            ),
            downloads_dir=tmp_path / "downloads",
        )
        first = asyncio.run(
            service.process_upload(
                "june.csv",
                b"date,amount,description\n"
                b"2026-06-01,-10.00,Grocery\n"
                b"2026-07-04,-20.00,Train\n",
            )
        )
        second = asyncio.run(
            service.process_upload(
                "july.csv",
                b"date,amount,description\n"
                b"2026-07-04,-20.00,Train\n"
                b"2026-08-04,-30.00,Grocery\n",
            )
        )

        assert first["new_transaction_count"] == 2
        assert second["new_transaction_count"] == 1
        assert second["duplicate_count"] == 1
        assert categorized == ["Grocery", "Train", "Grocery"]
        assert resolved_people == ["Grocery", "Train", "Grocery"]

        restarted_history = ExpenseHistoryService(DatabaseDatasetStore(factory))
        july = restarted_history.list_expenses(year=2026, month=7)
        assert july["total_count"] == 1
        assert july["items"][0]["description"] == "Train"
        assert restarted_history.summary(people=["Household"])["expense_count"] == 3
    finally:
        engine.dispose()
