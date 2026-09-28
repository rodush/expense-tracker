from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

APP_JS = Path(__file__).parents[1] / "app" / "static" / "app.js"
INDEX_HTML = Path(__file__).parents[1] / "app" / "templates" / "index.html"
PACKAGE_JSON = Path(__file__).parents[1] / "frontend" / "package.json"
client = TestClient(app)


def test_vendored_chartjs_asset_is_served_locally() -> None:
    response = client.get("/static/vendor/chart.umd.min.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "Chart.js v4.5.1" in response.text[:100]


def test_dashboard_ui_exposes_stable_controls_and_summary_regions() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    for element_id in (
        "fileInput",
        "uploadButton",
        "loading",
        "error",
        "resultsTable",
        "categoryFilter",
        "whoFilter",
        "clearFilters",
        "dashboardLoading",
        "dashboardEmpty",
        "dashboardError",
        "downloadLink",
        "filteredDownloadLink",
    ):
        assert f'id="{element_id}"' in html
    assert '<script src="/static/vendor/chart.umd.min.js"></script>' in html
    assert '<script src="/static/app.js"></script>' in html
    assert html.index("chart.umd.min.js") < html.index("/static/app.js")


def test_dashboard_contract_fetches_summary_for_selected_filters() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "payload.dataset_id" in javascript
    assert "params.append('category', value)" in javascript
    assert "params.append('who', value)" in javascript
    assert "/datasets/${encodeURIComponent(datasetId)}/summary?${params}" in javascript
    assert "clearFilters.addEventListener('click'" in javascript
    assert "/datasets/${encodeURIComponent(datasetId)}/export?${params}" in javascript


def test_dashboard_uses_pinned_chartjs_and_updates_existing_chart() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")
    package = PACKAGE_JSON.read_text(encoding="utf-8")

    assert '"chart.js": "4.5.1"' in package
    assert "new Chart(categoryChartCanvas" in javascript
    assert "categoryChart.update();" in javascript
    assert "type: 'doughnut'" in javascript
    assert "Math.abs(item.amount)" in javascript
    assert "categoryChartAmounts[context.dataIndex]" in javascript
    assert "createElementNS" not in javascript


def test_uploaded_values_are_rendered_as_text_not_html() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "cell.textContent = value ?? '';" in javascript
    assert "tr.innerHTML" not in javascript
    assert "${row." not in javascript


def test_dashboard_contract_surfaces_upload_and_summary_failures() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "if (!response.ok)" in javascript
    assert "payload.detail || 'Upload failed.'" in javascript
    assert "payload.detail || 'Unable to load summary.'" in javascript
    assert "showDashboardError(err.message)" in javascript
