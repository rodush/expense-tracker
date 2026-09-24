# Issue 16: Add reusable datasets and summary aggregation

## Title
Define a normalized dataset boundary and expose summary aggregation for dashboard reporting

## Description
The current upload flow produces a preview and temporary CSV but does not create a reusable, validated data set for reporting. This issue adds the server-side boundary needed to support dashboard summaries, filterable charts, and consistent export behavior across the application.

## Scope
- Return a dataset identifier from upload processing or equivalent server-side handle
- Store normalized categorized rows in a short-lived dataset repository
- Define the dataset schema for amount, category, who, description, and metadata
- Add a summary endpoint that aggregates totals and counts by category and person
- Support multi-value category and person filters with explicit validation
- Handle empty-result, malformed value, and invalid dataset scenarios with clear errors
- Ensure the download flow and reporting flow operate from the same normalized data

## Acceptance Criteria
- Upload responses include a reusable dataset identifier or equivalent reference
- Summary endpoints return totals, counts, and per-category/person breakdowns
- Invalid dataset IDs, invalid filters, and malformed amounts fail with actionable responses
- Filtering semantics are consistent across the API, dashboard, and exports
- Backend tests cover the key aggregation and validation cases
