from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Dataset, ExpenseRow


class DatasetRepository:
    """Persistence operations for imports and the canonical expense ledger."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        rows: Sequence[tuple[Decimal, dict[str, object]]],
        owner_id: str | None = None,
    ) -> Dataset:
        dataset = Dataset(owner_id=owner_id, row_count=len(rows))
        self._session.add(dataset)
        self._session.flush()
        dataset.rows = [
            self._new_expense(
                dataset.id, f"{dataset.id}:{position}", position, amount, values
            )
            for position, (amount, values) in enumerate(rows)
        ]
        self._session.flush()
        return dataset

    def add_import(
        self,
        source_hash: str,
        rows: Sequence[tuple[str, Decimal, dict[str, Any]]],
        row_count: int,
        duplicate_count: int,
        columns: Sequence[str],
        category_column_added: bool,
        owner_id: str | None = None,
    ) -> Dataset:
        dataset = Dataset(
            owner_id=owner_id,
            source_hash=source_hash,
            row_count=row_count,
            duplicate_count=duplicate_count,
            columns=list(columns),
            category_column_added=category_column_added,
        )
        self._session.add(dataset)
        self._session.flush()
        dataset.rows = [
            self._new_expense(dataset.id, key, position, amount, values)
            for position, (key, amount, values) in enumerate(rows)
        ]
        self._session.flush()
        return dataset

    def _new_expense(
        self,
        dataset_id: str,
        record_key: str,
        position: int,
        amount: Decimal,
        values: dict[str, Any],
    ) -> ExpenseRow:
        transaction_date = values.get("date")
        try:
            parsed_date = date.fromisoformat(str(transaction_date))
        except ValueError, TypeError:
            parsed_date = None
        return ExpenseRow(
            dataset_id=dataset_id,
            record_key=record_key,
            position=position,
            transaction_date=parsed_date,
            amount=amount,
            description=str(values.get("description", "") or ""),
            category=str(values.get("category", "Other") or "Other"),
            who=str(values.get("who", "General") or "General"),
            values=values,
        )

    def get_import_by_hash(
        self, source_hash: str, owner_id: str | None
    ) -> Dataset | None:
        statement = (
            select(Dataset)
            .options(selectinload(Dataset.rows))
            .where(Dataset.source_hash == source_hash, Dataset.owner_id == owner_id)
        )
        return self._session.scalar(statement)

    def existing_record_keys(
        self, record_keys: Sequence[str], owner_id: str | None
    ) -> set[str]:
        if not record_keys:
            return set()
        statement = (
            select(ExpenseRow.record_key)
            .join(Dataset)
            .where(Dataset.owner_id == owner_id, ExpenseRow.record_key.in_(record_keys))
        )
        return set(self._session.scalars(statement))

    def list_expenses(
        self,
        owner_id: str | None,
        categories: Sequence[str],
        people: Sequence[str],
        date_from: date | None,
        date_to: date | None,
        offset: int,
        limit: int | None,
    ) -> tuple[list[ExpenseRow], int]:
        conditions = self._expense_conditions(
            owner_id, categories, people, date_from, date_to
        )
        statement = select(ExpenseRow).join(Dataset).where(*conditions)
        count = (
            self._session.scalar(select(func.count()).select_from(statement.subquery()))
            or 0
        )
        query = statement.order_by(ExpenseRow.transaction_date.desc(), ExpenseRow.id)
        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        rows = list(self._session.scalars(query))
        return rows, count

    def summarize_expenses(
        self,
        owner_id: str | None,
        categories: Sequence[str],
        people: Sequence[str],
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        conditions = self._expense_conditions(
            owner_id, categories, people, date_from, date_to
        )
        total = self._session.scalar(
            select(func.coalesce(func.sum(ExpenseRow.amount), 0))
            .select_from(ExpenseRow)
            .join(Dataset)
            .where(*conditions)
        )
        count = (
            self._session.scalar(
                select(func.count())
                .select_from(ExpenseRow)
                .join(Dataset)
                .where(*conditions)
            )
            or 0
        )
        category_rows = self._grouped_amounts(conditions, ExpenseRow.category)
        who_rows = self._grouped_amounts(conditions, ExpenseRow.who)
        return {
            "total_amount": Decimal(total or 0),
            "expense_count": count,
            "categories": category_rows,
            "who": who_rows,
        }

    def _grouped_amounts(self, conditions, field) -> list[dict[str, Any]]:
        grouped = (
            select(field, func.sum(ExpenseRow.amount), func.count())
            .select_from(ExpenseRow)
            .join(Dataset)
            .where(*conditions)
            .group_by(field)
            .order_by(field)
        )
        return [
            {"name": name, "amount": Decimal(amount), "count": count}
            for name, amount, count in self._session.execute(grouped)
        ]

    def filter_options(self, owner_id: str | None) -> dict[str, list[Any]]:
        return {
            "categories": list(
                self._session.scalars(
                    select(ExpenseRow.category)
                    .join(Dataset)
                    .where(Dataset.owner_id == owner_id)
                    .distinct()
                    .order_by(ExpenseRow.category)
                )
            ),
            "who": list(
                self._session.scalars(
                    select(ExpenseRow.who)
                    .join(Dataset)
                    .where(Dataset.owner_id == owner_id)
                    .distinct()
                    .order_by(ExpenseRow.who)
                )
            ),
            "years": list(
                self._session.scalars(
                    select(func.extract("year", ExpenseRow.transaction_date))
                    .join(Dataset)
                    .where(
                        Dataset.owner_id == owner_id,
                        ExpenseRow.transaction_date.is_not(None),
                    )
                    .distinct()
                    .order_by(func.extract("year", ExpenseRow.transaction_date).desc())
                )
            ),
        }

    def _expense_conditions(
        self,
        owner_id: str | None,
        categories: Sequence[str],
        people: Sequence[str],
        date_from: date | None,
        date_to: date | None,
    ) -> list[Any]:
        conditions = [Dataset.owner_id == owner_id]
        if categories:
            conditions.append(ExpenseRow.category.in_(categories))
        if people:
            conditions.append(ExpenseRow.who.in_(people))
        if date_from is not None:
            conditions.append(ExpenseRow.transaction_date >= date_from)
        if date_to is not None:
            conditions.append(ExpenseRow.transaction_date <= date_to)
        return conditions

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
        return dataset
