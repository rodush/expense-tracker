Created isolated worktree for branch `agents/expense-visualization-plan-filtering`

I’ll first map the existing frontend, backend, data model, and test structure, then I’ll turn that into an implementation plan with a visualization-library recommendation.

Find files matching `*`

Find files matching `**/*.{py,tsx,ts,js,jsx,json,toml,yml,yaml}`

Search for `expense|category|owner|user|dashboard|chart|visual`

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/README.md"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/pyproject.toml"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/app/main.py"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/app/config.py"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/app/static/app.js"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/app/templates/index.html"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/tests/test_category_and_gemini.py"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/tests/test_upload_parsing.py"
}

The repository is a small FastAPI app with a vanilla JavaScript/Pico UI: uploads are processed in one request, `who` and `category` are added server-side, and the only persisted artifact is a temporary CSV download. I’m checking categorization semantics and current validation conventions so the plan accounts for data contracts, filtering scope, and test coverage.

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/app/services/gemini_service.py"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/tests/test_config_hardening.py"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/.github/specs/README.md"
}

Read 
Completed with input: {
  "path": "/home/rodush/Work/expense-tracker.worktrees/expense-visualization-plan-filtering/.gitignore"
}

Ran terminal command: git status --short && git log -5 --oneline

## Current architecture

- Backend: FastAPI upload endpoint in `app/main.py`
- Categorization and `who` detection: `gemini_service.py`
- Configured categories: `config.py`
- Frontend: vanilla JavaScript in `app.js` and HTML in `index.html`
- The application currently processes one uploaded file, returns a preview, and creates a temporary CSV download. There is no database or persistent expense dataset.

## Recommended visualization library

Use **Chart.js**.

Reasons:

- Fits the existing lightweight vanilla-JavaScript frontend.
- Supports doughnut, bar, and stacked-bar charts without introducing a frontend framework.
- Responsive and easy to update when filters change.
- Smaller implementation and dependency footprint than Plotly or Apache ECharts.
- Suitable chart types:
  - Doughnut chart: total spending by category.
  - Bar chart: category totals with exact values.
  - Optional stacked bar chart: categories split by person.

Pin a known Chart.js version and load it through the project’s chosen dependency/static-asset mechanism rather than relying on an unpinned CDN URL.

## Backend plan

### 1. Define the reporting data contract

Add a reporting response containing:

- `total_amount`
- `expense_count`
- `categories`: category name, amount, count, percentage
- `who`: person name, amount, count
- `applied_filters`
- Optional `rows` or filtered preview data

Use the configured categories from `settings.allowed_categories`, including zero-value categories where useful for stable chart legends.

### 2. Introduce a dataset/reporting boundary

The current `/upload` response contains the processed rows but does not create a reusable dataset. Add an explicit dataset identifier and a short-lived server-side storage layer.

Recommended initial implementation:

- Store normalized categorized rows in memory or a temporary JSON/CSV-backed repository.
- Associate them with a UUID and expiration time.
- Keep `/download/{download_id}` behavior separate from reporting storage.
- Return a `dataset_id` from `/upload`.

For production use, replace this with a database-backed expense/session model.

### 3. Add an aggregation endpoint

Add an endpoint such as:

```text
GET /datasets/{dataset_id}/summary
```

Query parameters:

```text
category=Food&category=Transport
who=Roman&who=General
```

The endpoint should:

- Validate the dataset ID.
- Validate category values against configured categories.
- Validate `who` values discovered in the dataset.
- Apply both filters with AND semantics.
- Parse and validate `amount` as numeric data.
- Aggregate totals and counts by category and person.
- Return a clear 400 response for invalid filters or malformed amounts.
- Avoid exposing rows from another dataset.

### 4. Handle amount semantics explicitly

Before implementation, decide whether negative amounts represent refunds/income or whether they should be excluded. The summary must consistently define:

- Gross total versus net total.
- Currency handling.
- Rounding rules.
- Empty-result behavior.

Recommended default: treat uploaded amounts as signed values, aggregate net totals, and return zero-valued chart data with an explanatory empty state when filters match nothing.

### 5. Reuse the same normalized rows

Filtering and aggregation should operate on the same normalized representation used for:

- Preview rendering.
- CSV download.
- Category assignment.

This prevents discrepancies between the table, download, and charts.

## Frontend plan

### 1. Add a filter panel

In `index.html`, add:

- Multi-select category control.
- Multi-select “Who” control.
- Clear filters button.
- Optional summary text showing active filters.
- Disabled state until an upload has completed.

Populate both controls from backend response metadata rather than hardcoding names.

### 2. Add a visualization section

Add a dashboard section containing:

- Total expenses card.
- Expense count card.
- Doughnut chart for category distribution.
- Bar chart for category totals.
- Optional person/category breakdown chart.
- Accessible text summary or table equivalent for users who cannot interpret charts.

### 3. Update charts when filters change

In `app.js`:

- Save the returned `dataset_id`.
- Fetch summary data whenever a filter changes.
- Debounce rapid filter changes if requests are asynchronous.
- Destroy or update existing Chart.js instances before rendering replacements.
- Show loading, empty, and error states.
- Keep the table synchronized with the active filters, either by requesting filtered rows or filtering the local normalized preview.

### 4. Make rendering safe

The current table uses `innerHTML` with uploaded values in `app.js`. As part of this feature, render cell values using `textContent` or escaped DOM creation so descriptions cannot inject HTML or scripts.

### 5. Preserve download behavior

Clarify whether downloading should:

- Always download the full categorized dataset, or
- Download the currently filtered dataset.

Recommended: provide both explicit actions if needed, with the existing full export preserved and a separate “Download filtered results” endpoint.

## Testing plan

### Backend tests

Extend the existing tests in `test_category_and_gemini.py` to cover:

- Dataset ID returned after upload.
- Category-only filtering.
- Person-only filtering.
- Combined category/person filtering.
- Multiple selected values.
- Invalid category/person values.
- Unknown dataset IDs.
- Empty filtered results.
- Correct totals, counts, percentages, and rounding.
- Negative or malformed amounts according to the selected policy.
- Stable behavior when Gemini is unavailable.

### Frontend tests

Add browser-level tests if the project adopts a frontend test runner; otherwise test the API contract and manually verify:

- Upload initializes filters and charts.
- Every filter combination updates all visualizations.
- Clear filters restores the original totals.
- Empty results are clearly shown.
- Chart labels and tooltip values match the backend totals.
- Uploaded descriptions are rendered as text, not executable HTML.
- Keyboard and screen-reader access to filters and chart summaries.

### Validation

Run the existing test suite and Ruff checks after implementation:

```bash
uv run pytest
uv run ruff check
```

## Suggested implementation order

1. Decide amount/currency and filtered-download semantics.
2. Define normalized dataset and summary response schemas.
3. Add short-lived dataset storage.
4. Implement aggregation and filter validation.
5. Add backend tests.
6. Add frontend filter controls and loading/error states.
7. Integrate Chart.js and accessible summaries.
8. Synchronize table, charts, and downloads.
9. Perform browser and responsive-layout verification.
10. Update `README.md` with the new reporting workflow and API behavior.