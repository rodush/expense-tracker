from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import MAX_UPLOAD_SIZE_BYTES

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)


def test_upload_accepts_csv_and_adds_category_column() -> None:
    csv_content = (
        "date,amount,description\n"
        "2026-07-01,15.50,PAS543 Coffee Shop\n"
        "2026-07-02,48.00,KAARTNUMMER: **5006 Office supplies\n"
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


def test_preview_renderer_uses_text_nodes_for_uploaded_values() -> None:
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    assert "cell.textContent = value ?? '';" in app_js
    assert "tr.innerHTML" not in app_js


def test_full_download_remains_available_as_the_categorized_csv() -> None:
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


def test_upload_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/upload",
        files={"file": ("expenses.txt", b"not a spreadsheet", "text/plain")},
    )

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_path_traversal_filename() -> None:
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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "not-a-directory"
    output_path.write_text("blocking path", encoding="utf-8")
    monkeypatch.setattr("app.main.DOWNLOADS_DIR", output_path)

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


def test_upload_rejects_malformed_spreadsheet_content() -> None:
    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", b"\x80\x81\x82", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to parse file content."


def test_upload_rejects_files_over_the_configured_size_limit() -> None:
    oversized_content = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", oversized_content, "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Uploaded file is too large."
