# Issue 19: Add regression coverage for dashboard and reporting flows

## Title
Strengthen automated tests for filtering, aggregation, and frontend behavior

## Description
The reporting and dashboard features introduce multiple integration points: uploads, normalized storage, summary aggregation, chart updates, and filter validation. This issue adds the test coverage needed to prevent regressions and document the expected API and UI contracts.

## Scope
- Extend backend tests to cover dataset creation, filtering, aggregation, invalid inputs, and empty results
- Cover negative amounts, malformed values, and unavailable Gemini service behavior
- Validate frontend behavior for filter changes, empty states, and reset flows
- Check that chart values and labels match backend totals and filter inputs
- Run the project’s automated validation commands as part of the release gate

## Acceptance Criteria
- Backend regression tests cover the core reporting and validation scenarios
- Frontend or API contract tests cover dashboard filter changes and empty states
- Invalid dataset and filter inputs are exercised by automated tests
- Local and CI validation commands are documented and consistently invoked
- Test failures clearly identify the failing workflow or contract
