from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dependencies import get_upload_service
from app.main import create_app
from app.services.dataset_store import DatasetStore
from app.services.upload_service import MAX_UPLOAD_SIZE_BYTES, UploadService


async def _categorize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "category": "Food"} for row in rows]


test_store = DatasetStore()
app = create_app(data_store=test_store, categorizer=_categorize)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_test_store() -> None:
    test_store.clear()


def _override_upload_service(
    monkeypatch: pytest.MonkeyPatch,
    categorize=None,
    downloads_dir: Path | None = None,
) -> UploadService:
    configured_service: UploadService = app.state.upload_service
    service = UploadService(
        dataset_store=configured_service.dataset_store,
        categorize=categorize or configured_service.categorize,
        determine_who=configured_service.determine_who,
        downloads_dir=downloads_dir or configured_service.downloads_dir,
    )
    monkeypatch.setitem(app.dependency_overrides, get_upload_service, lambda: service)
    return service


def test_upload_accepts_csv_and_adds_category_column(client) -> None:
    csv_content = (
        "date,amount,description\n"
        "2026-07-01,-15.50,PAS543 Coffee Shop\n"
        "2026-07-02,-48.00,KAARTNUMMER: **5006 Office supplies\n"
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
        "who",
        "category",
    ]
    assert payload["preview"][0]["who"] == "Roman"
    assert payload["preview"][1]["who"] == "Oksana"


def test_upload_normalizes_dutch_bank_column_names(client) -> None:
    csv_content = (
        "Transactiedatum,Transactiebedrag,Omschrijving\n"
        "2026-07-01,-15.50,PAS543 Coffee Shop\n"
    )

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["columns"] == ["date", "amount", "description", "who", "category"]
    assert payload["preview"][0]["date"] == "2026-07-01"
    assert payload["preview"][0]["amount"] == 15.5
    assert payload["preview"][0]["description"] == "PAS543 Coffee Shop"


def test_upload_uses_configured_transaction_date_format() -> None:
    configured_service = UploadService(
        dataset_store=DatasetStore(),
        categorize=_categorize,
        determine_who=lambda _description: "General",
        downloads_dir=Path.cwd(),
        transaction_date_format="%d/%m/%Y",
    )

    _, _, normalized_rows = asyncio.run(
        configured_service._process_new_upload(
            "expenses.csv",
            b"date,amount,description\n01/07/2026,-15.50,Coffee\n",
            ".csv",
        )
    )

    assert normalized_rows[0]["date"] == "2026-07-01"


def test_upload_filters_credits_before_categorization_and_uses_absolute_debits(
    monkeypatch: pytest.MonkeyPatch, client
) -> None:
    categorized_input: list[dict[str, Any]] = []

    async def categorize(
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        categorized_input.extend(rows)
        return [{**row, "category": "Food"} for row in rows]

    _override_upload_service(monkeypatch, categorize=categorize)
    csv_content = (
        "date,amount,description\n"
        "2026-07-01,-15.50,Coffee\n"
        "2026-07-02,120.00,Card top-up\n"
        "2026-07-03,0.001,Small credit\n"
        "2026-07-04,-500.00,SEPA Overboeking                 "
        "IBAN: TEST        BIC: TEST                    "
        "Naam: Savings Account           Kenmerk: NOTPROVIDED\n"
        "2026-07-05,-2.75,Lunch\n"
    )

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode(), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(categorized_input) == 2
    assert [row["amount"] for row in categorized_input] == [15.5, 2.75]
    assert payload["row_count"] == 2
    assert [row["amount"] for row in payload["preview"]] == [2.75, 15.5]


def test_reuploading_identical_input_reuses_processed_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, client
) -> None:
    categorized_batches: list[list[dict[str, Any]]] = []

    async def categorize(
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        categorized_batches.append(rows)
        return [{**row, "category": "Food"} for row in rows]

    _override_upload_service(monkeypatch, categorize=categorize, downloads_dir=tmp_path)
    csv_content = b"date,amount,description\n2026-07-01,-15.50,Coffee\n"

    first_response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content, "text/csv")},
    )
    second_response = client.post(
        "/upload",
        files={"file": ("renamed.csv", csv_content, "text/csv")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_payload = first_response.json()
    second_payload = second_response.json()
    assert len(categorized_batches) == 1
    assert first_payload["preview"] == second_payload["preview"]
    assert first_payload["dataset_id"] == second_payload["dataset_id"]
    assert second_payload["new_transaction_count"] == 0
    assert second_payload["duplicate_count"] == 1
    assert client.get(f"/download/{second_payload['download_id']}").status_code == 200


def test_full_download_remains_available_as_the_categorized_csv(client) -> None:
    response = client.post(
        "/upload",
        files={
            "file": (
                "expenses.csv",
                b"date,amount,description\n2026-07-01,-15.50,Coffee\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    download = client.get(f"/download/{payload['download_id']}")

    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/csv")
    assert "date,amount,description,who,category" in download.text
    preview = payload["preview"][0]
    assert (
        f"{preview['date']},{preview['amount']},{preview['description']},"
        f"{preview['who']},{preview['category']}"
    ) in download.text


def test_upload_rejects_unsupported_file_type(client) -> None:
    response = client.post(
        "/upload",
        files={"file": ("expenses.txt", b"not a spreadsheet", "text/plain")},
    )

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_path_traversal_filename(client) -> None:
    response = client.post(
        "/upload",
        files={
            "file": (
                "../evil.csv",
                b"date,amount,description\n2026-07-01,15.50,Coffee\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert "invalid filename" in response.json()["detail"].lower()


def test_upload_returns_retryable_error_when_output_cannot_be_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, client
) -> None:
    output_path = tmp_path / "not-a-directory"
    output_path.write_text("blocking path", encoding="utf-8")
    _override_upload_service(monkeypatch, downloads_dir=output_path)

    response = client.post(
        "/upload",
        files={
            "file": (
                "expenses.csv",
                b"date,amount,description\n2026-07-01,15.50,Coffee\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 503
    assert "retry" in response.json()["detail"].lower()


def test_upload_rejects_malformed_spreadsheet_content(client) -> None:
    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", b"\x80\x81\x82", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to parse file content."


def test_upload_rejects_files_over_the_configured_size_limit(client) -> None:
    oversized_content = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", oversized_content, "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Uploaded file is too large."
