from __future__ import annotations

from pathlib import Path

APP_SOURCE = Path(__file__).parents[1] / "frontend" / "src" / "App.svelte"
INDEX_HTML = Path(__file__).parents[1] / "app" / "templates" / "index.html"


def test_dashboard_ui_exposes_stable_controls_and_summary_regions() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    component = APP_SOURCE.read_text(encoding="utf-8")

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
        assert f'id="{element_id}"' in component
    assert '<link rel="stylesheet" href="/static/frontend/app.css">' in html
    assert '<script type="module" src="/static/frontend/app.js"></script>' in html


def test_dashboard_contract_fetches_summary_for_selected_filters() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "payload.dataset_id" in component
    assert "params.append('category', value)" in component
    assert "params.append('who', value)" in component
    assert "/datasets/${encodeURIComponent(datasetId)}/summary?${params}" in component
    assert "/datasets/${encodeURIComponent(datasetId)}/export?${params}" in component


def test_uploaded_values_are_rendered_as_text_not_html() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "{row.description ?? ''}" in component
    assert "{@html" not in component


def test_preview_table_is_collapsible_and_description_is_last_and_bounded() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "<details>" in component
    assert "<summary>Categorized expenses (preview)</summary>" in component
    assert component.index("<th>Category</th>") < component.index("<th>Description</th>")
    assert '<col class="description-column">' in component
    assert "#resultsTable col.description-column" in component
    assert "width: 300px;" in component
    assert "text-overflow: ellipsis;" in component
    assert 'id="descriptionTooltip"' in component


def test_description_tooltip_tracks_pointer_and_repositions_at_viewport_edges() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "showDescriptionTooltip(index, row.description, event.clientX, event.clientY)" in component
    assert "window.innerWidth" in component
    assert "window.innerHeight" in component
    assert "aria-describedby={tooltipRowIndex === index ? 'descriptionTooltip' : undefined}" in component


def test_category_chart_assigns_a_unique_color_per_returned_category() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "new Map(items.map((item) => [item.name, item]))" in component
    assert "categories.map((_, index) => `hsl(" in component
    assert "categoryChart.data.datasets[0].backgroundColor = colors;" in component
    assert "backgroundColor: colors," in component


def test_dashboard_contract_surfaces_upload_and_summary_failures() -> None:
    component = APP_SOURCE.read_text(encoding="utf-8")

    assert "if (!response.ok)" in component
    assert "payload.detail || 'Upload failed.'" in component
    assert "payload.detail || 'Unable to load summary.'" in component
    assert "showDashboardError(err.message)" in component
