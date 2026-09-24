from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
DATASET_TTL_SECONDS = 60 * 60


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


@dataclass
class _StoredDataset:
    rows: list[dict[str, Any]]
    expires_at: float


class DatasetNotFoundError(KeyError):
    """Raised when a dataset is missing or has expired."""


class DatasetStore:
    def __init__(self, ttl_seconds: int = DATASET_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._datasets: dict[str, _StoredDataset] = {}
        self._lock = threading.Lock()

    def create(self, rows: Iterable[Mapping[str, Any]]) -> str:
        dataset_id = str(uuid.uuid4())
        with self._lock:
            self._purge_expired()
            self._datasets[dataset_id] = _StoredDataset(
                rows=normalize_rows(rows),
                expires_at=time.monotonic() + self._ttl_seconds,
            )
        return dataset_id

    def get(self, dataset_id: str) -> list[dict[str, Any]]:
        with self._lock:
            self._purge_expired()
            dataset = self._datasets.get(dataset_id)
            if dataset is None:
                raise DatasetNotFoundError(dataset_id)
            return [row.copy() for row in dataset.rows]

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired_ids = [
            dataset_id
            for dataset_id, dataset in self._datasets.items()
            if dataset.expires_at <= now
        ]
        for dataset_id in expired_ids:
            del self._datasets[dataset_id]


dataset_store = DatasetStore()
