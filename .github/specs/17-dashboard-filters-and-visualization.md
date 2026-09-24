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
