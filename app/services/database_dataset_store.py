from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
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

    def find_import(self, source_hash: str) -> dict[str, object] | None:
        with self._session_factory.begin() as session:
            dataset = DatasetRepository(session).get_import_by_hash(
                source_hash, owner_id=None
            )
            if dataset is None:
                return None
            return {
                "dataset_id": dataset.id,
                "row_count": dataset.row_count,
                "duplicate_count": dataset.duplicate_count,
                "columns": list(dataset.columns),
                "category_column_added": dataset.category_column_added,
                "rows": [dict(row.values) for row in dataset.rows],
            }

    def existing_record_keys(self, record_keys: Sequence[str]) -> set[str]:
        with self._session_factory() as session:
            return DatasetRepository(session).existing_record_keys(
                record_keys, owner_id=None
            )

    def import_rows(
        self,
        source_hash: str,
        row_count: int,
        rows: Sequence[tuple[str, Mapping[str, object]]],
        columns: Sequence[str],
        category_column_added: bool,
    ) -> tuple[str, list[dict[str, object]], int]:
        normalized_rows = [normalize_rows([values])[0] for _, values in rows]
        repository_rows = [
            (key, parse_amount(values.get("amount")), values)
            for (key, _), values in zip(rows, normalized_rows, strict=True)
        ]
        with self._session_factory.begin() as session:
            repository = DatasetRepository(session)
            previous_import = repository.get_import_by_hash(source_hash, owner_id=None)
            if previous_import is not None:
                return previous_import.id, [], row_count
            existing = repository.existing_record_keys(
                [key for key, _, _ in repository_rows], owner_id=None
            )
            new_rows = [item for item in repository_rows if item[0] not in existing]
            dataset = repository.add_import(
                source_hash=source_hash,
                rows=new_rows,
                row_count=row_count,
                duplicate_count=row_count - len(new_rows),
                columns=columns,
                category_column_added=category_column_added,
            )
            dataset_id = dataset.id
            inserted_rows = [dict(row.values) for row in dataset.rows]
            duplicate_count = dataset.duplicate_count
        return dataset_id, inserted_rows, duplicate_count

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

    def list_expenses(
        self,
        categories: Sequence[str] = (),
        people: Sequence[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int | None = 100,
    ) -> tuple[list[dict[str, object]], int]:
        with self._session_factory() as session:
            rows, total_count = DatasetRepository(session).list_expenses(
                owner_id=None,
                categories=categories,
                people=people,
                date_from=date_from,
                date_to=date_to,
                offset=offset,
                limit=limit,
            )
            return [dict(row.values) for row in rows], total_count

    def summarize_expenses(
        self,
        categories: Sequence[str] = (),
        people: Sequence[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, object]:
        with self._session_factory() as session:
            return DatasetRepository(session).summarize_expenses(
                owner_id=None,
                categories=categories,
                people=people,
                date_from=date_from,
                date_to=date_to,
            )

    def expense_filter_options(self) -> dict[str, list[object]]:
        with self._session_factory() as session:
            options = DatasetRepository(session).filter_options(owner_id=None)
            options["years"] = [int(year) for year in options["years"]]
            return options
