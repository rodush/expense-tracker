from __future__ import annotations

import calendar
import csv
import logging
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

from app.services.errors import ServiceError

logger = logging.getLogger("expense_tracker")


class ExpenseHistoryService:
    """Query the durable expense ledger across all uploaded statements."""

    def __init__(self, ledger_store) -> None:
        self.ledger_store = ledger_store

    def _filters(
        self,
        categories: list[str] | None,
        people: list[str] | None,
        date_from: date | None,
        date_to: date | None,
        year: int | None,
        month: int | None,
    ) -> tuple[list[str], list[str], date | None, date | None]:
        selected_categories = categories or []
        selected_people = people or []
        options = self.ledger_store.expense_filter_options()
        unknown_categories = sorted(
            set(selected_categories) - set(options["categories"])
        )
        unknown_people = sorted(set(selected_people) - set(options["who"]))
        if unknown_categories:
            raise ServiceError(
                400, f"Invalid category filter: {', '.join(unknown_categories)}"
            )
        if unknown_people:
            raise ServiceError(400, f"Invalid who filter: {', '.join(unknown_people)}")

        if month is not None and (month < 1 or month > 12):
            raise ServiceError(400, "Month must be between 1 and 12.")
        if year is not None and (year < 1 or year > 9999):
            raise ServiceError(400, "Year must be between 1 and 9999.")
        if month is not None and year is None:
            raise ServiceError(400, "A year is required when filtering by month.")
        if (year is not None or month is not None) and (
            date_from is not None or date_to is not None
        ):
            raise ServiceError(
                400, "Use either a date range or a year/month filter, not both."
            )
        if year is not None:
            if month is None:
                date_from, date_to = date(year, 1, 1), date(year, 12, 31)
            else:
                date_from = date(year, month, 1)
                date_to = date(year, month, calendar.monthrange(year, month)[1])
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ServiceError(400, "The start date must not be after the end date.")
        return selected_categories, selected_people, date_from, date_to

    def list_expenses(
        self,
        categories: list[str] | None = None,
        people: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        year: int | None = None,
        month: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        categories, people, date_from, date_to = self._filters(
            categories, people, date_from, date_to, year, month
        )
        items, total_count = self.ledger_store.list_expenses(
            categories, people, date_from, date_to, offset, limit
        )
        return {
            "items": items,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
        }

    def summary(
        self,
        categories: list[str] | None = None,
        people: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        categories, people, date_from, date_to = self._filters(
            categories, people, date_from, date_to, year, month
        )
        aggregate = self.ledger_store.summarize_expenses(
            categories, people, date_from, date_to
        )
        total = Decimal(aggregate["total_amount"])
        category_groups = aggregate["categories"]
        for item in category_groups:
            item["amount"] = float(item["amount"])
            item["percentage"] = (
                round(item["amount"] / float(total) * 100, 2) if total else 0.0
            )
        return {
            "total_amount": float(total),
            "expense_count": aggregate["expense_count"],
            "categories": category_groups,
            "who": [
                {**item, "amount": float(item["amount"])} for item in aggregate["who"]
            ],
            "applied_filters": {
                "category": categories,
                "who": people,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "year": year,
                "month": month,
            },
        }

    def filter_options(self) -> dict[str, list[Any]]:
        return self.ledger_store.expense_filter_options()

    def export_csv(self, **filters: Any) -> tuple[str, bool]:
        categories, people, date_from, date_to = self._filters(
            filters.get("categories"),
            filters.get("people"),
            filters.get("date_from"),
            filters.get("date_to"),
            filters.get("year"),
            filters.get("month"),
        )
        rows, _ = self.ledger_store.list_expenses(
            categories, people, date_from, date_to, offset=0, limit=None
        )
        output = StringIO(newline="")
        fieldnames = (
            list(dict.fromkeys(key for row in rows for key in row))
            if rows
            else ["date", "amount", "description", "who", "category"]
        )
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue(), bool(
            filters.get("categories")
            or filters.get("people")
            or filters.get("date_from")
            or filters.get("date_to")
            or filters.get("year")
            or filters.get("month")
        )
