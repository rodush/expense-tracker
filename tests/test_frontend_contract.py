from __future__ import annotations

from pathlib import Path

APP_JS = Path(__file__).parents[1] / "app" / "static" / "app.js"
INDEX_HTML = Path(__file__).parents[1] / "app" / "templates" / "index.html"


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
    assert '<script src="/static/app.js"></script>' in html


def test_dashboard_contract_fetches_summary_for_selected_filters() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "payload.dataset_id" in javascript
    assert "params.append('category', value)" in javascript
    assert "params.append('who', value)" in javascript
    assert "/datasets/${encodeURIComponent(datasetId)}/summary?${params}" in javascript
    assert "clearFilters.addEventListener('click'" in javascript
    assert "/datasets/${encodeURIComponent(datasetId)}/export?${params}" in javascript


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
