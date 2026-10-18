from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.dataset_store import DatasetStore


def _history_app() -> tuple[FastAPI, Counter[str]]:
    categorized: Counter[str] = Counter()

    async def categorize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        categorized.update(str(row["description"]) for row in rows)
        return [
            {
                **row,
                "category": "Transport"
                if "train" in str(row["description"]).casefold()
                else "Food",
            }
            for row in rows
        ]

    app = create_app(
        data_store=DatasetStore(),
        categorizer=categorize,
        who_resolver=lambda _description: "Household",
    )
    return app, categorized


def _upload(client: TestClient, content: bytes, filename: str = "bank.csv"):
    return client.post(
        "/upload",
        files={"file": (filename, content, "text/csv")},
    )


def test_history_deduplicates_overlapping_imports_and_filters_by_month() -> None:
    app, categorized = _history_app()
    with TestClient(app) as client:
        first = _upload(
            client,
            b"date,amount,description\n"
            b"2026-06-01,-10.00,Grocery\n"
            b"2026-07-04,-20.00,Train\n",
        )
        overlapping = _upload(
            client,
            b"date,amount,description\n"
            b"2026-07-04,-20.00,Train\n"
            b"2026-08-04,-30.00,Grocery\n",
            "overlap.csv",
        )

        assert first.status_code == overlapping.status_code == 200
        assert first.json()["new_transaction_count"] == 2
        assert overlapping.json()["new_transaction_count"] == 1
        assert overlapping.json()["duplicate_count"] == 1
        assert categorized == Counter({"Grocery": 2, "Train": 1})

        july = client.get("/expenses", params={"year": 2026, "month": 7})
        assert july.status_code == 200
        assert july.json()["total_count"] == 1
        assert july.json()["items"][0]["description"] == "Train"

        summary = client.get("/expenses/summary", params={"category": "Food"})
        assert summary.status_code == 200
        assert summary.json()["expense_count"] == 2
        assert summary.json()["total_amount"] == 40.0


def test_history_exports_filtered_rows() -> None:
    app, _ = _history_app()
    with TestClient(app) as client:
        response = _upload(
            client,
            b"date,amount,description\n2026-08-04,-30.00,Grocery\n",
        )
        assert response.status_code == 200

        exported = client.get(
            "/expenses/export",
            params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
        )
        assert exported.status_code == 200
        assert "Grocery" in exported.text
        assert "Transport" not in exported.text


def test_history_rejects_conflicting_or_invalid_date_filters() -> None:
    app, _ = _history_app()
    with TestClient(app) as client:
        conflicting = client.get(
            "/expenses", params={"year": 2026, "date_from": "2026-01-01"}
        )
        invalid_month = client.get("/expenses", params={"year": 2026, "month": 13})
        invalid_range = client.get(
            "/expenses", params={"date_from": "2026-12-31", "date_to": "2026-01-01"}
        )

        assert (
            conflicting.status_code
            == invalid_month.status_code
            == invalid_range.status_code
            == 400
        )
