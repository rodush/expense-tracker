from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal

from sqlalchemy.orm import sessionmaker

from app.db.repositories import DatasetRepository
from app.services.dataset_store import (
    DatasetNotFoundError,
    normalize_rows,
    parse_amount,
)


class DatabaseDatasetStore:
    """Persist normalized expense rows using the application's SQL database."""

    supports_download_regeneration = True

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def create(self, rows: Iterable[Mapping[str, object]]) -> str:
        normalized = normalize_rows(rows)
        repository_rows = [(parse_amount(row.get("amount")), row) for row in normalized]
        with self._session_factory.begin() as session:
            dataset = DatasetRepository(session).add(
                repository_rows,
            )
            dataset_id = dataset.id
        return dataset_id

    def get(self, dataset_id: str) -> list[dict[str, object]]:
        with self._session_factory.begin() as session:
            dataset = DatasetRepository(session).get(dataset_id, owner_id=None)
            rows = (
                [
                    {
                        **row.values,
                        "amount": float(Decimal(row.amount)),
                    }
                    for row in dataset.rows
                ]
                if dataset is not None
                else None
            )
        if rows is None:
            raise DatasetNotFoundError(dataset_id)
        return rows
