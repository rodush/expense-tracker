from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_accepts_csv_and_adds_category_column() -> None:
    csv_content = (
        "date,amount,description,purchaser\n"
        "2026-07-01,15.50,Coffee Shop,Jane Doe\n"
        "2026-07-02,48.00,Office supplies,John Smith\n"
    )

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["row_count"] == 2
    assert payload["category_column_added"] is True
    assert payload["columns"] == [
        "date",
        "amount",
        "description",
        "purchaser",
        "category",
    ]


def test_upload_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/upload",
        files={"file": ("expenses.txt", b"not a spreadsheet", "text/plain")},
    )

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
