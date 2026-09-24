from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_live_service() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "expense-categorizer"


def test_readiness_endpoint_reports_loaded_runtime() -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "expense-categorizer",
    }
