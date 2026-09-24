from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.main import app
from app.services import gemini_service
from app.services.gemini_service import normalize_category

client = TestClient(app)


def test_missing_required_columns_returns_clear_validation_error() -> None:
    csv_content = "date,amount\n2026-07-01,15.50\n"

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 400
    assert "missing required columns" in response.json()["detail"].lower()
    assert "description" in response.json()["detail"].lower()


def test_environment_file_is_loaded_into_process_environment() -> None:
    assert settings.allowed_categories
    assert "Other" in settings.allowed_categories
    assert normalize_category("Other") == "Other"


def test_category_settings_are_loaded_from_config() -> None:
    assert settings.allowed_categories
    assert (
        normalize_category(settings.allowed_categories[0])
        == settings.allowed_categories[0]
    )
    assert "Other" in settings.allowed_categories


def test_categorize_dataframe_batches_records_and_maps_indices(
    monkeypatch: MonkeyPatch,
) -> None:
    captured_batch_sizes: list[int] = []

    def fake_call_gemini_batch(batch: list[dict[str, object]]) -> dict[int, str]:
        captured_batch_sizes.append(len(batch))
        return {int(cast(int, item["record_index"])): "Other" for item in batch}

    monkeypatch.setattr(gemini_service, "_call_gemini_batch", fake_call_gemini_batch)

    rows = [{"description": f"Expense {index}"} for index in range(52)]
    categorized_rows = gemini_service.categorize_dataframe(rows)

    assert len(categorized_rows) == 52
    assert captured_batch_sizes == [50, 2]
    assert categorized_rows[0]["category"] == "Other"
    assert categorized_rows[51]["category"] == "Other"


def test_categorize_dataframe_async_sends_batches_concurrently(
    monkeypatch: MonkeyPatch,
) -> None:
    batch_barrier = threading.Barrier(2)

    def fake_classify_batch(
        batch: list[dict[str, object]], start_index: int
    ) -> dict[int, str]:
        batch_barrier.wait(timeout=1)
        return {start_index + offset: "Other" for offset in range(len(batch))}

    monkeypatch.setattr(gemini_service, "_classify_batch", fake_classify_batch)

    rows = [{"description": f"Expense {index}"} for index in range(52)]
    categorized_rows = asyncio.run(gemini_service.categorize_dataframe_async(rows))

    assert len(categorized_rows) == 52
    assert categorized_rows[0]["category"] == "Other"
    assert categorized_rows[51]["category"] == "Other"


def test_normalize_category_rejects_unknown_values_and_falls_back_to_other() -> None:
    assert normalize_category("Mystery Category") == "Other"


def test_categorize_dataframe_falls_back_when_gemini_is_unavailable(
    monkeypatch: MonkeyPatch,
) -> None:
    rows = [{"description": "Coffee at the cafe"}]
    categorized_rows = gemini_service.categorize_dataframe(rows)

    assert categorized_rows[0]["category"] == normalize_category("Food")


def test_categorize_dataframe_falls_back_when_gemini_call_raises(
    monkeypatch: MonkeyPatch,
) -> None:
    def explode(batch: list[dict[str, object]]) -> dict[int, str]:
        raise RuntimeError("transient gemini failure")

    monkeypatch.setattr(gemini_service, "_call_gemini_batch", explode)

    rows = [{"description": "Coffee at the cafe"}]
    categorized_rows = gemini_service.categorize_dataframe(rows)

    assert categorized_rows[0]["category"] == normalize_category("Food")


def test_categorize_dataframe_retries_transient_gemini_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    attempts = 0

    def fail_once(batch: list[dict[str, object]]) -> dict[int, str]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary timeout")
        return {int(cast(int, batch[0]["record_index"])): "Shopping"}

    monkeypatch.setattr(gemini_service, "_call_gemini_batch", fail_once)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda _: None)

    categorized_rows = gemini_service.categorize_dataframe(
        [{"description": "Amazon store"}]
    )

    assert attempts == 2
    assert categorized_rows[0]["category"] == "Shopping"


def test_categorize_dataframe_uses_fallback_after_retry_limit(
    monkeypatch: MonkeyPatch,
) -> None:
    attempts = 0

    def always_times_out(batch: list[dict[str, object]]) -> dict[int, str]:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("temporary timeout")

    monkeypatch.setattr(gemini_service, "_call_gemini_batch", always_times_out)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda _: None)

    categorized_rows = gemini_service.categorize_dataframe(
        [{"description": "Amazon store"}]
    )

    assert attempts == gemini_service.GEMINI_MAX_RETRIES + 1
    assert categorized_rows[0]["category"] == "Shopping"


def test_categorize_dataframe_async_falls_back_when_batch_times_out(
    monkeypatch: MonkeyPatch,
) -> None:
    async def timeout(awaitable: Any, **kwargs: Any) -> dict[int, str]:
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", timeout)

    categorized_rows = asyncio.run(
        gemini_service.categorize_dataframe_async([{"description": "Amazon store"}])
    )

    assert categorized_rows[0]["category"] == "Shopping"


def test_ui_route_serves_the_browser_page() -> None:
    response = cast(Any, client).get("/ui")

    assert response.status_code == 200
    assert "Expenses Categorizer" in response.text
    assert "Upload & Categorize" in response.text


def test_upload_returns_downloadable_csv_file() -> None:
    csv_content = "date,amount,description\n2026-07-01,15.50,PAS543 Coffee Shop\n"

    response = client.post(
        "/upload",
        files={"file": ("expenses.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    download_id = payload["download_id"]
    assert download_id
    assert payload["preview"][0]["who"] == "Roman"

    download_response = client.get(f"/download/{download_id}")
    assert download_response.status_code == 200
    assert "who" in download_response.text
    assert "category" in download_response.text
