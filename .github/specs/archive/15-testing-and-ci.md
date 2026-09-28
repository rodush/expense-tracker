# Issue 15: Strengthen automated testing and CI

## Title
Expand automated validation and continuous integration coverage

## Description
The project would benefit from stronger test coverage and a more reliable CI pipeline. This issue focuses on adding regression tests for critical flows, enforcing quality checks automatically, and making it easier to catch issues before they reach production.

## Scope
- Add or expand tests for configuration, error handling, uploads, and core processing flows
- Introduce linting, formatting, and test execution checks in CI
- Ensure critical paths are covered by automated tests
- Document the expected local and CI validation commands
- Make failures actionable for contributors and maintainers

## Acceptance Criteria
- Core functionality has automated regression coverage
- CI runs linting and tests on every relevant change
- The test and validation workflow is documented clearly
- Failures in CI provide enough context for rapid resolution
