# Issue 20: Document the reporting workflow and rollout approach

## Title
Document the dashboard workflow, API behavior, and operational release notes

## Description
As the reporting feature is introduced, the project needs clear user-facing and operator-facing documentation. This issue captures the update to the project documentation so contributors, testers, and maintainers know how the new dataset, filters, charts, and exports work together.

## Scope
- Update the main README with the new upload, dataset, and dashboard workflow
- Document the summary API contract and filter semantics
- Explain amount handling, empty-state behavior, and filtering defaults
- Record the validation commands and QA expectations for the reporting feature
- Summarize operational questions such as storage lifetime, export behavior, and future persistence strategy

## Acceptance Criteria
- The README explains how uploads become dataset-backed summaries and charts
- API behavior and filter semantics are easy to discover for contributors
- Amount policy, export behavior, and empty-result handling are documented
- Validation commands and expected QA checks are included in project docs
- Future persistence and production follow-up work are explicitly called out
