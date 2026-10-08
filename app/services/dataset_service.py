from __future__ import annotations

import csv
import logging
from decimal import Decimal
from io import StringIO
from typing import Any

from app.services.dataset_store import DatasetNotFoundError, DatasetStore, parse_amount
from app.services.errors import ServiceError

logger = logging.getLogger("expense_tracker")


class DatasetService:
    def __init__(
        self, dataset_store: DatasetStore, allowed_categories: tuple[str, ...]
    ) -> None:
        self.dataset_store = dataset_store
        self.allowed_categories = allowed_categories

    def filter_rows(
        self,
        dataset_id: str,
        categories: list[str] | None = None,
        people: list[str] | None = None,
        operation: str = "summary",
    ) -> list[dict[str, Any]]:
        try:
            rows = self.dataset_store.get(dataset_id)
        except DatasetNotFoundError as exc:
            logger.warning(
                "dataset.not_found",
                extra={"operation": operation, "dataset_id": dataset_id},
            )
            raise ServiceError(404, "Dataset not found.") from exc

        selected_categories = categories or []
        selected_who = people or []
        unknown_categories = sorted(
            set(selected_categories).difference(self.allowed_categories)
        )
        if unknown_categories:
            raise ServiceError(
                400, f"Invalid category filter: {', '.join(unknown_categories)}"
            )

        available_who = {str(row.get("who", "")) for row in rows}
        unknown_who = sorted(set(selected_who).difference(available_who))
        if unknown_who:
            raise ServiceError(400, f"Invalid who filter: {', '.join(unknown_who)}")

        return [
            row
            for row in rows
            if (not selected_categories or row.get("category") in selected_categories)
            and (not selected_who or row.get("who") in selected_who)
        ]

    def summarize(
        self,
        dataset_id: str,
        categories: list[str] | None = None,
        people: list[str] | None = None,
    ) -> dict[str, Any]:
        selected_categories = categories or []
        selected_who = people or []
        filtered_rows = self.filter_rows(dataset_id, selected_categories, selected_who)
        rows = self.dataset_store.get(dataset_id)
        try:
            amounts = [parse_amount(row.get("amount")) for row in filtered_rows]
        except (TypeError, ValueError) as exc:
            raise ServiceError(400, str(exc)) from exc

        def aggregate(field: str) -> list[dict[str, Any]]:
            names = (
                list(self.allowed_categories)
                if field == "category"
                else sorted(
                    {
                        str(row.get(field, ""))
                        for row in rows
                        if row.get(field) is not None
                    }
                )
            )
            names = [
                name
                for name in names
                if any(row.get(field) == name for row in filtered_rows)
            ]
            return [
                {
                    "name": name,
                    "amount": float(
                        sum(
                            (
                                amount
                                for row, amount in zip(filtered_rows, amounts)
                                if row.get(field) == name
                            ),
                            Decimal("0.00"),
                        )
                    ),
                    "count": sum(row.get(field) == name for row in filtered_rows),
                }
                for name in names
            ]

        total_amount_decimal = sum(amounts, Decimal("0.00"))
        total_amount = float(total_amount_decimal)
        categories_summary = aggregate("category")
        for item in categories_summary:
            item["percentage"] = (
                round(item["amount"] / total_amount * 100, 2) if total_amount else 0.0
            )

        logger.info(
            "summary.completed",
            extra={
                "operation": "summary",
                "dataset_id": dataset_id,
                "record_count": len(filtered_rows),
            },
        )
        return {
            "dataset_id": dataset_id,
            "total_amount": total_amount,
            "expense_count": len(filtered_rows),
            "categories": categories_summary,
            "who": aggregate("who"),
            "applied_filters": {"category": selected_categories, "who": selected_who},
        }

    def export_csv(
        self,
        dataset_id: str,
        categories: list[str] | None = None,
        people: list[str] | None = None,
    ) -> tuple[str, bool]:
        rows = self.filter_rows(dataset_id, categories, people, operation="export")
        output = StringIO(newline="")
        fieldnames = (
            list(rows[0])
            if rows
            else ["date", "amount", "description", "who", "category"]
        )
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        logger.info(
            "dataset.exported",
            extra={
                "operation": "export",
                "dataset_id": dataset_id,
                "record_count": len(rows),
                "filtered": bool(categories or people),
            },
        )
        return output.getvalue(), bool(categories or people)
