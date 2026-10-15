from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Dataset, ExpenseRow


class DatasetRepository:
    """Persistence operations for datasets, without API or upload policy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        rows: Sequence[tuple[Decimal, dict[str, object]]],
        owner_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> Dataset:
        dataset = Dataset(owner_id=owner_id, expires_at=expires_at)
        dataset.rows = [
            ExpenseRow(position=position, amount=amount, values=values)
            for position, (amount, values) in enumerate(rows)
        ]
        self._session.add(dataset)
        self._session.flush()
        return dataset

    def get(self, dataset_id: str, owner_id: str | None) -> Dataset | None:
        statement = (
            select(Dataset)
            .options(selectinload(Dataset.rows))
            .where(Dataset.id == dataset_id)
        )
        statement = statement.where(Dataset.owner_id == owner_id)
        dataset = self._session.scalar(statement)
        if dataset is None:
            return None
        expires_at = dataset.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                self._session.delete(dataset)
                self._session.flush()
                return None
        return dataset
