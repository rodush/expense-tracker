from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.dataset_store import dataset_store

client = TestClient(app)


def _upload_dataset() -> str:
    csv_content = (
        "date,amount,description\n"
        "2026-07-01,10.00,PAS543 shop purchase\n"
        "2026-07-02,20.00,kaartnummer: **5006 taxi\n"
        "2026-07-03,-5.00,shared shop refund\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode(), "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["dataset_id"]


def test_upload_returns_dataset_id_and_summary_aggregates_signed_amounts() -> None:
    dataset_id = _upload_dataset()

    response = client.get(f"/datasets/{dataset_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["total_amount"] == 25.0
    assert payload["expense_count"] == 3
    assert payload["applied_filters"] == {"category": [], "who": []}
    assert {item["name"]: item for item in payload["who"]} == {
        "General": {"name": "General", "amount": -5.0, "count": 1},
        "Oksana": {"name": "Oksana", "amount": 20.0, "count": 1},
        "Roman": {"name": "Roman", "amount": 10.0, "count": 1},
    }


def test_summary_applies_multiple_filters_with_and_semantics() -> None:
    dataset_id = _upload_dataset()

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params=[("category", "Shopping"), ("who", "Roman")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_amount"] == 10.0
    assert payload["expense_count"] == 1
    assert payload["applied_filters"] == {
        "category": ["Shopping"],
        "who": ["Roman"],
    }


def test_summary_supports_multiple_values_and_reports_percentages() -> None:
    dataset_id = dataset_store.create(
        [
            {"amount": "10.005", "category": "Food", "who": "Roman"},
            {"amount": "20", "category": "Shopping", "who": "Oksana"},
            {"amount": "-5", "category": "Food", "who": "Roman"},
        ]
    )

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params=[("category", "Food"), ("category", "Shopping")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_amount"] == 25.01
    assert payload["expense_count"] == 3
    assert payload["applied_filters"]["category"] == ["Food", "Shopping"]
    categories = {item["name"]: item for item in payload["categories"]}
    assert categories["Food"] == {
        "name": "Food",
        "amount": 5.01,
        "count": 2,
        "percentage": 20.03,
    }
    assert categories["Shopping"]["percentage"] == 79.97


def test_summary_returns_zero_values_for_empty_filter_result() -> None:
    dataset_id = _upload_dataset()

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params={"category": "Utilities"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_amount"] == 0.0
    assert payload["expense_count"] == 0
    assert all(item["amount"] == 0.0 for item in payload["categories"])
    assert all(item["percentage"] == 0.0 for item in payload["categories"])
    assert payload["who"] == []


def test_summary_rejects_invalid_filters_and_unknown_datasets() -> None:
    dataset_id = _upload_dataset()

    invalid_category = client.get(
        f"/datasets/{dataset_id}/summary",
        params={"category": "Not configured"},
    )
    invalid_who = client.get(
        f"/datasets/{dataset_id}/summary",
        params={"who": "Nobody"},
    )
    unknown_dataset = client.get(
        "/datasets/00000000-0000-0000-0000-000000000000/summary"
    )

    assert invalid_category.status_code == 400
    assert invalid_who.status_code == 400
    assert unknown_dataset.status_code == 404


def test_summary_rejects_malformed_amount_from_dataset_store(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        dataset_store,
        "get",
        lambda _: [{"amount": "not-a-number", "category": "Food", "who": "Roman"}],
    )

    response = client.get("/datasets/00000000-0000-0000-0000-000000000000/summary")

    assert response.status_code == 400
    assert response.json()["detail"] == "amount must be numeric"


def test_filtered_export_uses_summary_filters_and_csv_contract() -> None:
    dataset_id = _upload_dataset()

    response = client.get(
        f"/datasets/{dataset_id}/export",
        params=[("category", "Shopping"), ("who", "Roman")],
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "filtered" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows == [
        {
            "date": "2026-07-01",
            "amount": "10.0",
            "description": "PAS543 shop purchase",
            "who": "Roman",
            "category": "Shopping",
        }
    ]


def test_filtered_export_rejects_invalid_filters_and_unknown_datasets() -> None:
    dataset_id = _upload_dataset()

    invalid_filter = client.get(
        f"/datasets/{dataset_id}/export",
        params={"category": "Not configured"},
    )
    unknown_dataset = client.get(
        "/datasets/00000000-0000-0000-0000-000000000000/export"
    )

    assert invalid_filter.status_code == 400
    assert unknown_dataset.status_code == 404


def test_upload_rejects_malformed_amount() -> None:
    response = client.post(
        "/upload",
        files={
            "file": (
                "expenses.csv",
                b"date,amount,description\n2026-07-01,not-a-number,Coffee\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "amount must be numeric"
