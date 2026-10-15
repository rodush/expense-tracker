---
name: tester
description: Ensures decent test coverage and tests that are passing
---

<!-- Tip: Use /create-skill in chat to generate content with agent assistance -->

Run the relevant project test suite and report the exact commands and results.

- Python tests run from the repository root with `uv run pytest`.
- Frontend tests run from `frontend/` with `npm test`, followed by
  `npm run check` and `npm run build` when frontend code changes.
- For behavior changes, first add or update a focused regression test, then
  implement the change and run the test (TDD).
- Do not claim coverage thresholds or passing checks unless the repository
  defines and the run verifies them.
