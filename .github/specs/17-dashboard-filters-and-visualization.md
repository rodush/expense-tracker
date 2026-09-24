# Issue 17: Add dashboard filters and chart-based reporting

## Title
Build the filter panel and visualization dashboard for expense insights

## Description
The app needs a user-facing dashboard that lets users explore aggregate spending by category and person. This issue covers the frontend controls and chart rendering needed to present totals, filters, and drill-down summaries without introducing a heavy framework.

## Scope
- Add category and person multi-select controls to the UI
- Show active-filter state and a clear reset action for the dashboard
- Fetch summary data from the backend whenever filters change
- Render category totals and breakdowns with accessible chart components
- Keep summary cards, charts, and table data synchronized with the active filters
- Show loading, empty, and error states for dashboard operations

## Acceptance Criteria
- Users can filter expenses by category and person multi-select controls
- The dashboard updates when filters change and resets correctly when cleared
- The UI displays totals, counts, and category breakdowns using chart and summary components
- Empty states and invalid filter responses are communicated clearly to users
- The dashboard remains usable with keyboard and screen-reader-friendly controls

## Implemented contract and assumptions

The dashboard uses `GET /datasets/{dataset_id}/summary` and repeated query
parameters (`category` and `who`) for multi-select filters. The response is
expected to contain `dataset_id`, signed `total_amount`, `expense_count`,
`categories` (each with `name`, `amount`, `count`, and `percentage`),
`who` (each with `name`, `amount`, and `count`), and `applied_filters`.
Category values are combined with OR semantics, while category and person
filters are combined with AND semantics. A valid filter with no matches is a
successful response with zero totals.

The current UI intentionally avoids a chart dependency. It renders an
accessible SVG bar chart alongside equivalent category and person tables; the
tables are the text alternative and remain available when the chart has no
data. Filter options are populated from the uploaded preview because the
summary response does not currently expose option metadata. The existing
download remains an explicit full-dataset export, while the preview table is
filtered locally to stay synchronized with the summary.
