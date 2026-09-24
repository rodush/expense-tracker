from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.logging_config import StructuredFormatter
from app.main import app

client = TestClient(app)


def test_requests_receive_and_log_a_request_id(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="expense_tracker"):
        response = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    assert any(
        record.message == "request.completed" and record.request_id == "request-123"
        for record in caplog.records
    )


def test_structured_formatter_redacts_arbitrary_sensitive_fields() -> None:
    record = logging.LogRecord(
        name="expense_tracker",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="provider failed",
        args=(),
        exc_info=None,
    )
    record.api_key = "secret-token"
    record.file_name = "expenses.csv"

    payload = json.loads(StructuredFormatter().format(record))

    assert payload["message"] == "provider failed"
    assert payload["file_name"] == "expenses.csv"
    assert "api_key" not in payload
    assert "secret-token" not in json.dumps(payload)
