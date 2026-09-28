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


def test_uploaded_values_are_rendered_as_text_not_html() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "cell.textContent = value ?? '';" in javascript
    assert "tr.innerHTML" not in javascript
    assert "${row." not in javascript


def test_preview_table_is_collapsible_and_description_is_last_and_bounded() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "<details>" in html
    assert "<summary>Categorized expenses (preview)</summary>" in html
    assert html.index("<th>Category</th>") < html.index("<th>Description</th>")
    assert '<col class="description-column">' in html
    assert "#resultsTable col.description-column" in html
    assert "width: 300px;" in html
    assert "text-overflow: ellipsis;" in html
    assert 'id="descriptionTooltip"' in html


def test_description_tooltip_tracks_pointer_and_repositions_at_viewport_edges() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "positionDescriptionTooltip(event.clientX, event.clientY)" in javascript
    assert "window.innerWidth" in javascript
    assert "window.innerHeight" in javascript
    assert "cell.setAttribute('aria-describedby', 'descriptionTooltip')" in javascript


def test_category_chart_assigns_a_unique_color_per_returned_category() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "new Map(items.map((item) => [item.name, item]))" in javascript
    assert "categories.map((_, index) => `hsl(" in javascript
    assert "categoryChart.data.datasets[0].backgroundColor = colors;" in javascript
    assert "backgroundColor: colors," in javascript


def test_dashboard_contract_surfaces_upload_and_summary_failures() -> None:
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "if (!response.ok)" in javascript
    assert "payload.detail || 'Upload failed.'" in javascript
    assert "payload.detail || 'Unable to load summary.'" in javascript
    assert "showDashboardError(err.message)" in javascript
