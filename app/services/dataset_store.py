from __future__ import annotations

import threading
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from math import isnan
from typing import Any, Protocol

import pandas as pd

MONEY_QUANTUM = Decimal("0.01")


def parse_amount(value: Any) -> Decimal:
    """Parse a finite expense amount and normalize it to cents."""
    if isinstance(value, bool):
        raise TypeError("amount must be numeric")
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation, ValueError:
        raise ValueError("amount must be numeric") from None
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    missing = pd.isna(value)
    if not hasattr(missing, "__len__") and bool(missing):
        return None
    if isinstance(value, float) and isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def normalize_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized_row = {str(key): _json_value(value) for key, value in row.items()}
        normalized_row["amount"] = float(parse_amount(normalized_row.get("amount")))
        normalized.append(normalized_row)
    return normalized


class DatasetNotFoundError(KeyError):
    """Raised when an import batch is missing."""


class DatasetStoreBackend(Protocol):
    def create(self, rows: Iterable[Mapping[str, Any]]) -> str: ...

    def get(self, dataset_id: str) -> list[dict[str, Any]]: ...


class LedgerStoreBackend(DatasetStoreBackend, Protocol):
    def find_import(self, source_hash: str) -> dict[str, Any] | None: ...

    def existing_record_keys(self, record_keys: Sequence[str]) -> set[str]: ...

    def import_rows(
        self,
        source_hash: str,
        row_count: int,
        rows: Sequence[tuple[str, Mapping[str, Any]]],
        columns: Sequence[str],
        category_column_added: bool,
    ) -> tuple[str, list[dict[str, Any]], int]: ...

    def list_expenses(
        self,
        categories: Sequence[str] = (),
        people: Sequence[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int | None = 100,
    ) -> tuple[list[dict[str, Any]], int]: ...

    def summarize_expenses(
        self,
        categories: Sequence[str] = (),
        people: Sequence[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]: ...

    def expense_filter_options(self) -> dict[str, list[Any]]: ...


@dataclass
class _StoredDataset:
    rows: list[dict[str, Any]]


class DatasetStore:
    """Non-persistent ledger store for isolated tests and explicit injection."""

    def __init__(self) -> None:
        self._datasets: dict[str, _StoredDataset] = {}
        self._imports_by_hash: dict[str, dict[str, Any]] = {}
        self._record_keys: set[str] = set()
        self._lock = threading.Lock()

    def clear(self) -> None:
        """Remove all records; intended for isolated tests."""
        with self._lock:
            self._datasets.clear()
            self._imports_by_hash.clear()
            self._record_keys.clear()

    def create(self, rows: Iterable[Mapping[str, Any]]) -> str:
        dataset_id = str(uuid.uuid4())
        with self._lock:
            self._datasets[dataset_id] = _StoredDataset(rows=normalize_rows(rows))
        return dataset_id

    def get(self, dataset_id: str) -> list[dict[str, Any]]:
        with self._lock:
            dataset = self._datasets.get(dataset_id)
            if dataset is None:
                raise DatasetNotFoundError(dataset_id)
            return [row.copy() for row in dataset.rows]

    def find_import(self, source_hash: str) -> dict[str, Any] | None:
        with self._lock:
            imported = self._imports_by_hash.get(source_hash)
            return dict(imported) if imported is not None else None

    def existing_record_keys(self, record_keys: Iterable[str]) -> set[str]:
        with self._lock:
            return set(record_keys).intersection(self._record_keys)

    def import_rows(
        self,
        source_hash: str,
        row_count: int,
        rows: Iterable[tuple[str, Mapping[str, Any]]],
        columns: Iterable[str],
        category_column_added: bool,
    ) -> tuple[str, list[dict[str, Any]], int]:
        with self._lock:
            previous = self._imports_by_hash.get(source_hash)
            if previous is not None:
                return previous["dataset_id"], [], row_count
            new_rows = [
                (key, normalize_rows([row])[0])
                for key, row in rows
                if key not in self._record_keys
            ]
            dataset_id = str(uuid.uuid4())
            inserted_rows = [row for _, row in new_rows]
            self._datasets[dataset_id] = _StoredDataset(rows=inserted_rows)
            self._record_keys.update(key for key, _ in new_rows)
            duplicate_count = row_count - len(inserted_rows)
            self._imports_by_hash[source_hash] = {
                "dataset_id": dataset_id,
                "row_count": row_count,
                "duplicate_count": duplicate_count,
                "columns": list(columns),
                "category_column_added": category_column_added,
                "rows": inserted_rows,
            }
            return dataset_id, [row.copy() for row in inserted_rows], duplicate_count

    def list_expenses(
        self,
        categories: Iterable[str] = (),
        people: Iterable[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int | None = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        selected_categories = set(categories)
        selected_people = set(people)
        with self._lock:
            rows = [
                row.copy() for batch in self._datasets.values() for row in batch.rows
            ]
        filtered = [
            row
            for row in rows
            if (not selected_categories or row.get("category") in selected_categories)
            and (not selected_people or row.get("who") in selected_people)
            and (date_from is None or str(row.get("date", "")) >= date_from.isoformat())
            and (date_to is None or str(row.get("date", "")) <= date_to.isoformat())
        ]
        filtered.sort(key=lambda row: str(row.get("date", "")), reverse=True)
        total_count = len(filtered)
        page = filtered[offset:] if limit is None else filtered[offset : offset + limit]
        return page, total_count

    def summarize_expenses(
        self,
        categories: Iterable[str] = (),
        people: Iterable[str] = (),
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        rows, _ = self.list_expenses(categories, people, date_from, date_to, limit=None)
        total = sum((parse_amount(row.get("amount")) for row in rows), Decimal("0.00"))

        def grouped(field: str) -> list[dict[str, Any]]:
            groups: dict[str, list[Decimal]] = {}
            for row in rows:
                name = str(row.get(field, ""))
                amount = parse_amount(row.get("amount"))
                current = groups.setdefault(name, [Decimal("0.00"), Decimal(0)])
                current[0] += amount
                current[1] += 1
            return [
                {"name": name, "amount": amount, "count": int(count)}
                for name, (amount, count) in sorted(groups.items())
            ]

        return {
            "total_amount": total,
            "expense_count": len(rows),
            "categories": grouped("category"),
            "who": grouped("who"),
        }

    def expense_filter_options(self) -> dict[str, list[Any]]:
        with self._lock:
            rows = [row for batch in self._datasets.values() for row in batch.rows]
        years = sorted(
            {int(str(row["date"])[:4]) for row in rows if row.get("date")},
            reverse=True,
        )
        return {
            "categories": sorted(
                {str(row["category"]) for row in rows if row.get("category")}
            ),
            "who": sorted({str(row["who"]) for row in rows if row.get("who")}),
            "years": years,
        }


dataset_store = DatasetStore()
